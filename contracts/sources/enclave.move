module suiverify::enclave;

use std::bcs;
use std::string::String;
use sui::ed25519;
use sui::nitro_attestation::NitroAttestationDocument;
use fun to_pcrs as NitroAttestationDocument.to_pcrs;


// Constants
const EInvalidPCRs: u64 = 0;
const EInvalidConfigVersion: u64 = 1;
const EInvalidCap: u64 = 2;
const EInvalidOwner: u64 = 3;
const EWrongVersion: u64 = 4;
const ECannotDestroyCurrentEnclave: u64 = 5;

// Version
const VERSION: u64 = 0;

// PCR0: Enclave image file
// PCR1: Enclave Kernel
// PCR2: Enclave application
public struct Pcrs(vector<u8>, vector<u8>, vector<u8>) has copy, drop, store;

public struct EnclaveConfig<phantom T> has key {
    id: UID,
    name: String,
    pcrs: Pcrs,
    capability_id: ID,
    version: u64,
    current_enclave_id: Option<ID>,  // Track the current active enclave Objects id
}

// A verified enclave instance, with its public key
public struct Enclave<phantom T> has key {
    id: UID,
    pk: vector<u8>,
    config_version: u64,
    owner: address,
    version: u64,
}

// A capability to update the enclave config.
public struct Cap<phantom T> has key, store {
    id: UID,
}

// An intent message, used for wrapping enclave messages.
public struct IntentMessage<T: drop> has copy, drop {
    intent: u8,
    timestamp_ms: u64,
    payload: T,
}

/// One-time witness for enclave module
public struct ENCLAVE has drop {}

/// Initialize the enclave module - creates Cap and EnclaveConfig
fun init(otw: ENCLAVE, ctx: &mut TxContext) {
    let cap = new_cap(otw, ctx);

    cap.create_enclave_config(
        b"validation enclave".to_string(),
        x"000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", // pcr0 - will be updated with real values
        x"000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", // pcr1 - will be updated with real values
        x"000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", // pcr2 - will be updated with real values
        ctx,
    );

    transfer::public_transfer(cap, ctx.sender())
}

//  Migration function for upgradeability
entry fun migrate<T>(
    config: &mut EnclaveConfig<T>,
    cap: &Cap<T>
) {
    assert!(cap.id.to_inner() == config.capability_id, EInvalidCap);
    assert!(config.version < VERSION, EInvalidConfigVersion);
    config.version = VERSION;
}

/// Create a new `Cap` using a `witness` T from a module.
public fun new_cap<T: drop>(_: T, ctx: &mut TxContext): Cap<T> {
    Cap {
        id: object::new(ctx),
    }
}

public fun create_enclave_config<T: drop>(
    cap: &Cap<T>,
    name: String,
    pcr0: vector<u8>,
    pcr1: vector<u8>,
    pcr2: vector<u8>,
    ctx: &mut TxContext,
) {
    let enclave_config = EnclaveConfig<T> {
        id: object::new(ctx),
        name,
        pcrs: Pcrs(pcr0, pcr1, pcr2),
        capability_id: cap.id.to_inner(),
        version: 0,
        current_enclave_id: option::none(),  // No enclave registered yet
    };

    transfer::share_object(enclave_config);
}

public fun register_enclave<T>(
    enclave_config: &mut EnclaveConfig<T>,  // Changed to mutable
    cap: &Cap<T>,
    document: NitroAttestationDocument,
    ctx: &mut TxContext,
) {
    // Verify cap is valid for this config
    cap.assert_is_valid_for_config(enclave_config);
    
    let pk = enclave_config.load_pk(&document);

    let enclave = Enclave<T> {
        id: object::new(ctx),
        pk,
        config_version: enclave_config.version,
        owner: ctx.sender(),
        version: VERSION,
    };

    // Update the current enclave ID in config
    let enclave_id = object::id(&enclave);
    enclave_config.current_enclave_id = option::some(enclave_id);

    transfer::share_object(enclave);
}

public fun verify_signature<T, P: drop>(
    enclave: &Enclave<T>,
    intent_scope: u8,
    timestamp_ms: u64,
    payload: P,
    signature: &vector<u8>,
): bool {
    let intent_message = create_intent_message(intent_scope, timestamp_ms, payload);
    let payload = bcs::to_bytes(&intent_message);
    return ed25519::ed25519_verify(signature, &enclave.pk, &payload)
}

public fun update_pcrs<T: drop>(
    config: &mut EnclaveConfig<T>,
    cap: &Cap<T>,
    pcr0: vector<u8>,
    pcr1: vector<u8>,
    pcr2: vector<u8>,
) {
    assert!(config.version == VERSION, EWrongVersion);
    cap.assert_is_valid_for_config(config);
    config.pcrs = Pcrs(pcr0, pcr1, pcr2);
    config.version = config.version + 1;
    
    // When PCRs are updated, clear the current enclave as it's no longer valid
    config.current_enclave_id = option::none();
}

public fun update_name<T: drop>(config: &mut EnclaveConfig<T>, cap: &Cap<T>, name: String) {
    cap.assert_is_valid_for_config(config);
    config.name = name;
}

public fun pcr0<T>(config: &EnclaveConfig<T>): &vector<u8> {
    &config.pcrs.0
}

public fun pcr1<T>(config: &EnclaveConfig<T>): &vector<u8> {
    &config.pcrs.1
}

public fun pcr2<T>(config: &EnclaveConfig<T>): &vector<u8> {
    &config.pcrs.2
}

public fun pk<T>(enclave: &Enclave<T>): &vector<u8> {
    &enclave.pk
}

public fun destroy_old_enclave<T>(
    e: Enclave<T>, 
    config: &EnclaveConfig<T>,
    cap: &Cap<T>
) {
    // Verify cap is valid for this config
    cap.assert_is_valid_for_config(config);
    
    // Check if this is the current enclave
    let enclave_id = object::id(&e);
    if (option::is_some(&config.current_enclave_id)) {
        let current_id = *option::borrow(&config.current_enclave_id);
        assert!(enclave_id != current_id, ECannotDestroyCurrentEnclave);
    };
    
    // Also check version is old
    assert!(e.config_version < config.version, EInvalidConfigVersion);
    
    let Enclave { id, .. } = e;
    id.delete();
}

public fun deploy_old_enclave_by_owner<T>(e: Enclave<T>, ctx: &mut TxContext) {
    assert!(e.owner == ctx.sender(), EInvalidOwner);
    let Enclave { id, .. } = e;
    id.delete();
}

// Helper function to check if an enclave is the current one
public fun is_current_enclave<T>(config: &EnclaveConfig<T>, enclave: &Enclave<T>): bool {
    if (option::is_some(&config.current_enclave_id)) {
        let current_id = *option::borrow(&config.current_enclave_id);
        object::id(enclave) == current_id
    } else {
        false
    }
}

// Get current enclave ID if exists
public fun current_enclave_id<T>(config: &EnclaveConfig<T>): Option<ID> {
    config.current_enclave_id
}

fun assert_is_valid_for_config<T>(cap: &Cap<T>, enclave_config: &EnclaveConfig<T>) {
    assert!(cap.id.to_inner() == enclave_config.capability_id, EInvalidCap);
}

fun load_pk<T>(enclave_config: &EnclaveConfig<T>, document: &NitroAttestationDocument): vector<u8> {
    assert!(document.to_pcrs() == enclave_config.pcrs, EInvalidPCRs);

    (*document.public_key()).destroy_some()
}

fun to_pcrs(document: &NitroAttestationDocument): Pcrs {
    let pcrs = document.pcrs();
    Pcrs(*pcrs[0].value(), *pcrs[1].value(), *pcrs[2].value())
}

fun create_intent_message<P: drop>(intent: u8, timestamp_ms: u64, payload: P): IntentMessage<P> {
    IntentMessage {
        intent,
        timestamp_ms,
        payload,
    }
}