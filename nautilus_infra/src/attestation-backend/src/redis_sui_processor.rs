// Redis consumer using redis-rs that polls verification data and executes Sui CLI commands
use anyhow::{Result, anyhow};
use redis::{Client, Commands, RedisResult, Value};
use serde::{Deserialize, Serialize};
use tokio::time::{Duration, Instant};
use tracing::{error, info, warn};
use fastcrypto::{ed25519::Ed25519KeyPair, traits::Signer};
use chrono::DateTime;
use hex;
use base64::{Engine as _, engine::general_purpose};
use std::process::Command;
use std::collections::HashMap;

// DID type constants (matching your Move contract)
const DID_AGE_VERIFY: u8 = 1;        // Contract value for age verification
const DID_CITIZENSHIP_VERIFY: u8 = 2; // Contract value for citizenship verification

// Redis message structure from your verification service
#[derive(Debug, Clone, Deserialize, Serialize)]
struct VerificationMessage {
    user_wallet: String,
    #[serde(deserialize_with = "deserialize_string_to_u8")]
    did_id: u8,  // Parse string to u8
    result: String,
    evidence_hash: String,
    verified_at: String,
}

// Custom deserializer to handle string to u8 conversion
fn deserialize_string_to_u8<'de, D>(deserializer: D) -> Result<u8, D::Error>
where
    D: serde::Deserializer<'de>,
{
    use serde::de::{self, Visitor};
    
    struct StringToU8Visitor;
    
    impl<'de> Visitor<'de> for StringToU8Visitor {
        type Value = u8;
        
        fn expecting(&self, formatter: &mut std::fmt::Formatter) -> std::fmt::Result {
            formatter.write_str("a string or integer that can be converted to u8")
        }
        
        fn visit_str<E>(self, value: &str) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            value.parse::<u8>().map_err(de::Error::custom)
        }
        
        fn visit_u64<E>(self, value: u64) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            if value <= u8::MAX as u64 {
                Ok(value as u8)
            } else {
                Err(de::Error::custom(format!("u64 value {} is too large for u8", value)))
            }
        }
        
        fn visit_i64<E>(self, value: i64) -> Result<Self::Value, E>
        where
            E: de::Error,
        {
            if value >= 0 && value <= u8::MAX as i64 {
                Ok(value as u8)
            } else {
                Err(de::Error::custom(format!("i64 value {} is out of range for u8", value)))
            }
        }
    }
    
    deserializer.deserialize_any(StringToU8Visitor)
}

// Throughput tracker
#[derive(Debug)]
pub struct ThroughputTracker {
    total_messages: u64,
    start_time: Instant,
    last_report_time: Instant,
}

impl ThroughputTracker {
    pub fn new() -> Self {
        let now = Instant::now();
        Self {
            total_messages: 0,
            start_time: now,
            last_report_time: now,
        }
    }

    pub fn record_message(&mut self) {
        self.total_messages += 1;
    }

    pub fn get_throughput(&self) -> f64 {
        let elapsed = self.start_time.elapsed().as_secs_f64();
        if elapsed > 0.0 {
            self.total_messages as f64 / elapsed
        } else {
            0.0
        }
    }

    pub fn maybe_report(&mut self, interval_secs: u64) -> bool {
        let elapsed = self.last_report_time.elapsed();
        
        if elapsed >= Duration::from_secs(interval_secs) {
            let throughput = self.get_throughput();
            info!("THROUGHPUT: {:.1} messages/sec (total: {})", throughput, self.total_messages);
            self.last_report_time = Instant::now();
            true
        } else {
            false
        }
    }
}

pub struct RedisSuiProcessor {
    keypair: Ed25519KeyPair,
    redis_client: Client,
    stream_name: String,
    consumer_group: String,
    consumer_name: String,
    throughput_tracker: ThroughputTracker,
    // Sui contract parameters
    package_id: String,
    registry_id: String,
    cap_id: String,
    clock_id: String,
}

impl RedisSuiProcessor {
    const REPORT_INTERVAL_SECS: u64 = 10;

    pub fn new(keypair: Ed25519KeyPair) -> Result<Self> {
        // Redis Cloud credentials (hardcoded for now)
        let redis_url = "redis://default:8GYkgUdA0XwfqNbdMg5hl6oc1f9wUpH0@redis-18401.c261.us-east-1-4.ec2.redns.redis-cloud.com:18401";
        
        let client = Client::open(redis_url)
            .map_err(|e| anyhow!("Failed to create Redis client: {}", e))?;

        Ok(RedisSuiProcessor {
            keypair,
            redis_client: client,
            stream_name: "verification_stream".to_string(),
            consumer_group: "attestation_processors".to_string(),
            consumer_name: "rust_processor_1".to_string(),
            throughput_tracker: ThroughputTracker::new(),
            package_id: "0x3611276dabf733007d7975e17989e505eb93e11f4998f93d5c74c3a44231833d".to_string(),
            registry_id: "0xea43902e5184fc2cbbc194e63c236321d7cd4aebd006b2d4a7c76f8f03f194b9".to_string(),
            cap_id: "0x678a8ad11edf87246cafad705bed96960990b8d94c7708a0dce4ba68bfeec13a".to_string(),
            clock_id: "0x0000000000000000000000000000000000000000000000000000000000000006".to_string(),
        })
    }

    pub async fn start_processing(&mut self) -> Result<()> {
        info!("Starting Redis-Sui processor...");
        info!("Contract parameters:");
        info!("   Package: {}", self.package_id);
        info!("   Registry: {}", self.registry_id);
        info!("   Cap: {}", self.cap_id);
        info!("   Stream: {}", self.stream_name);
        info!("   Consumer Group: {}", self.consumer_group);
        info!("   Consumer Name: {}", self.consumer_name);
        
        // Test sui client configuration
        self.test_sui_client().await?;

        // Test Redis connection
        self.test_redis_connection().await?;

        // Create consumer group (ignore error if it already exists)
        self.create_consumer_group().await;

        // Start consuming messages
        loop {
            match self.consume_messages().await {
                Ok(message_count) => {
                    if message_count == 0 {
                        // No messages, wait a bit
                        tokio::time::sleep(Duration::from_millis(1000)).await;
                    }
                }
                Err(e) => {
                    error!("Redis consumption error: {}", e);
                    tokio::time::sleep(Duration::from_secs(5)).await;
                }
            }
        }
    }

    async fn test_redis_connection(&self) -> Result<()> {
        info!("Testing Redis connection...");
        
        let mut con = self.redis_client.get_connection()
            .map_err(|e| anyhow!("Failed to get Redis connection: {}", e))?;
        
        let pong: String = redis::cmd("PING").query(&mut con)
            .map_err(|e| anyhow!("Redis PING failed: {}", e))?;
        
        if pong == "PONG" {
            info!("✅ Redis connection successful");
            
            // Check if stream exists
            let exists: bool = con.exists(&self.stream_name)
                .map_err(|e| anyhow!("Failed to check stream existence: {}", e))?;
            
            if exists {
                // Use simple XLEN command to get stream length
                let length: i64 = redis::cmd("XLEN")
                    .arg(&self.stream_name)
                    .query(&mut con)
                    .map_err(|e| anyhow!("Failed to get stream length: {}", e))?;
                
                info!("✅ Stream '{}' exists with {} messages", self.stream_name, length);
            } else {
                info!("ℹ️ Stream '{}' does not exist yet, will be created when first message arrives", self.stream_name);
            }
            
            Ok(())
        } else {
            Err(anyhow!("Redis PING returned unexpected response: {}", pong))
        }
    }

    async fn create_consumer_group(&self) {
        info!("Creating consumer group '{}'...", self.consumer_group);
        
        match self.redis_client.get_connection() {
            Ok(mut con) => {
                // Try to create consumer group (ignore error if it already exists)
                let result: RedisResult<String> = redis::cmd("XGROUP")
                    .arg("CREATE")
                    .arg(&self.stream_name)
                    .arg(&self.consumer_group)
                    .arg("0")
                    .arg("MKSTREAM")
                    .query(&mut con);
                
                match result {
                    Ok(_) => info!("✅ Consumer group '{}' created successfully", self.consumer_group),
                    Err(e) => {
                        if e.to_string().contains("BUSYGROUP") {
                            info!("ℹ️ Consumer group '{}' already exists", self.consumer_group);
                        } else {
                            warn!("Failed to create consumer group: {}", e);
                        }
                    }
                }
            }
            Err(e) => {
                warn!("Failed to get Redis connection for consumer group creation: {}", e);
            }
        }
    }

    async fn consume_messages(&mut self) -> Result<usize> {
        let mut con = self.redis_client.get_connection()
            .map_err(|e| anyhow!("Failed to get Redis connection: {}", e))?;
        
        // Use raw Redis command for XREADGROUP - more compatible with older redis-rs versions
        let result: RedisResult<redis::Value> = redis::cmd("XREADGROUP")
            .arg("GROUP")
            .arg(&self.consumer_group)
            .arg(&self.consumer_name)
            .arg("COUNT")
            .arg(1)  // Read one message at a time for simplicity
            .arg("BLOCK")
            .arg(1000)
            .arg("STREAMS")
            .arg(&self.stream_name)
            .arg(">")
            .query(&mut con);
        
        match result {
            Ok(redis::Value::Bulk(streams)) => {
                let mut message_count = 0;
                
                for stream in streams {
                    if let redis::Value::Bulk(stream_data) = stream {
                        if stream_data.len() >= 2 {
                            // stream_data[0] is stream name, stream_data[1] is messages
                            if let redis::Value::Bulk(messages) = &stream_data[1] {
                                for message in messages {
                                    if let redis::Value::Bulk(msg_data) = message {
                                        if msg_data.len() >= 2 {
                                            // msg_data[0] is message ID, msg_data[1] is fields
                                            let message_id = redis::from_redis_value::<String>(&msg_data[0])?;
                                            
                                            if let redis::Value::Bulk(fields) = &msg_data[1] {
                                                let mut field_map = std::collections::HashMap::new();
                                                
                                                // Parse field-value pairs
                                                for i in (0..fields.len()).step_by(2) {
                                                    if i + 1 < fields.len() {
                                                        let field_name = redis::from_redis_value::<String>(&fields[i])?;
                                                        let field_value = fields[i + 1].clone();
                                                        field_map.insert(field_name, field_value);
                                                    }
                                                }
                                                
                                                message_count += 1;
                                                self.throughput_tracker.record_message();
                                                
                                                info!("Processing message ID: {}", message_id);
                                                
                                                match self.process_redis_message(&message_id, &field_map).await {
                                                    Ok(_) => {
                                                        // Acknowledge the message
                                                        let _: RedisResult<i32> = redis::cmd("XACK")
                                                            .arg(&self.stream_name)
                                                            .arg(&self.consumer_group)
                                                            .arg(&message_id)
                                                            .query(&mut con);
                                                        info!("✅ Message {} processed and acknowledged", message_id);
                                                    }
                                                    Err(e) => {
                                                        error!("Failed to process message {}: {}", message_id, e);
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
                // Report throughput
                self.throughput_tracker.maybe_report(Self::REPORT_INTERVAL_SECS);
                
                Ok(message_count)
            }
            Ok(redis::Value::Nil) => {
                // No messages available
                Ok(0)
            }
            Err(e) => {
                if e.to_string().contains("NOGROUP") {
                    warn!("Consumer group doesn't exist, recreating...");
                    self.create_consumer_group().await;
                    return Ok(0);
                }
                Err(anyhow!("Failed to read from Redis stream: {}", e))
            }
            Ok(other) => {
                warn!("Unexpected Redis response type: {:?}", other);
                Ok(0)
            }
        }
    }

    async fn process_redis_message(&mut self, message_id: &str, fields: &HashMap<String, Value>) -> Result<()> {
        info!("Processing Redis message {}: {:?}", message_id, fields);

        // Helper function to extract string from Redis Value
        let get_string_field = |field_name: &str| -> Result<String> {
            match fields.get(field_name) {
                Some(value) => {
                    redis::from_redis_value::<String>(value)
                        .map_err(|e| anyhow!("Cannot convert field {} to string: {}", field_name, e))
                },
                None => Err(anyhow!("Missing field: {}", field_name)),
            }
        };

        // Convert HashMap to VerificationMessage
        let verification = VerificationMessage {
            user_wallet: get_string_field("user_wallet")?,
            did_id: get_string_field("did_id")?
                .parse::<u8>()
                .map_err(|e| anyhow!("Invalid did_id: {}", e))?,
            result: get_string_field("result")?,
            evidence_hash: get_string_field("evidence_hash")?,
            verified_at: get_string_field("verified_at")?,
        };
        
        info!("User: {}, DID: {}, Result: {}", 
              verification.user_wallet, verification.did_id, verification.result);
        
        // Process the verification
        if let Some(user_did_id) = self.execute_start_verification(
            &verification.user_wallet,
            verification.did_id,
        ).await? {
            info!("UserDID created successfully: {}", user_did_id);
            
            if verification.result == "verified" {
                info!("Processing verified result - calling update_verification_status");
                
                let signature = self.generate_nautilus_signature(&verification)?;
                let signature_timestamp_ms = self.parse_timestamp_to_ms(&verification.verified_at)?;
                
                self.execute_update_verification_status(
                    &verification.user_wallet,
                    &user_did_id,
                    true,
                    signature,
                    signature_timestamp_ms,
                    &verification.evidence_hash,
                ).await?;
            } else {
                info!("Skipping update for non-verified result: {}", verification.result);
            }
        } else {
            warn!("Could not extract UserDID ID, skipping update_verification_status");
        }

        Ok(())
    }

    async fn test_sui_client(&self) -> Result<()> {
        info!("Testing sui client configuration...");
        
        let output = Command::new("sui")
            .args(["client", "active-address"])
            .output()
            .map_err(|e| anyhow!("Failed to execute sui client: {}", e))?;

        if output.status.success() {
            let active_address = String::from_utf8_lossy(&output.stdout).trim().to_string();
            info!("Sui client active address: {}", active_address);
            
            // Test gas balance
            let gas_output = Command::new("sui")
                .args(["client", "gas"])
                .output()
                .map_err(|e| anyhow!("Failed to check gas: {}", e))?;
                
            if gas_output.status.success() {
                info!("Gas coins available");
                info!("Gas info: {}", String::from_utf8_lossy(&gas_output.stdout).lines().take(3).collect::<Vec<_>>().join(" | "));
            } else {
                warn!("Could not check gas coins: {}", String::from_utf8_lossy(&gas_output.stderr));
            }
        } else {
            return Err(anyhow!("Sui client not configured properly: {}", String::from_utf8_lossy(&output.stderr)));
        }
        
        Ok(())
    }

    async fn execute_start_verification(
        &self,
        user_address: &str,
        redis_did_id: u8,
    ) -> Result<Option<String>> {
        info!("Executing start_verification transaction...");
        
        // Map Redis DID ID to contract DID type:
        // Redis 0 → Contract 1 (DID_AGE_VERIFY)
        // Redis 1 → Contract 2 (DID_CITIZENSHIP_VERIFY)
        let contract_did_type = match redis_did_id {
            0 => DID_AGE_VERIFY,        // Age verification
            1 => DID_CITIZENSHIP_VERIFY, // Citizenship verification
            _ => {
                warn!("Unknown DID ID from Redis: {}, defaulting to age verification", redis_did_id);
                DID_AGE_VERIFY
            }
        };
        
        info!("Mapping: Redis DID {} → Contract DID {}", redis_did_id, contract_did_type);
        
        // Execute sui client call command for start_verification
        let output = Command::new("sui")
            .args([
                "client",
                "call",
                "--package", &self.package_id,
                "--module", "did_registry",
                "--function", "start_verification",
                "--args", 
                &self.registry_id,              // registry
                &self.cap_id,                   // cap
                user_address,                   // user_address
                &contract_did_type.to_string(), // did_type (contract value)
                &self.clock_id,                 // clock
                "--gas-budget", "10000000"
            ])
            .output()
            .map_err(|e| anyhow!("Failed to execute sui command: {}", e))?;

        // Process the output
        if output.status.success() {
            info!("start_verification executed successfully for user: {}", user_address);
            let output_str = String::from_utf8_lossy(&output.stdout);
            info!("Output: {}", output_str);
            
            // Extract UserDID object ID from the transaction output
            if let Some(user_did_id) = extract_user_did_id(&output_str) {
                info!("Extracted UserDID ID: {}", user_did_id);
                return Ok(Some(user_did_id));
            } else {
                warn!("Could not extract UserDID ID from transaction output");
            }
            
            if !output.stderr.is_empty() {
                warn!("Warnings: {}", String::from_utf8_lossy(&output.stderr));
            }
        } else {
            error!("start_verification failed for user: {}", user_address);
            error!("Exit code: {}", output.status.code().unwrap_or(-1));
            error!("STDERR: {}", String::from_utf8_lossy(&output.stderr));
            error!("STDOUT: {}", String::from_utf8_lossy(&output.stdout));
            
            return Err(anyhow!("Transaction execution failed with exit code: {} - STDERR: {} - STDOUT: {}", 
                output.status.code().unwrap_or(-1),
                String::from_utf8_lossy(&output.stderr),
                String::from_utf8_lossy(&output.stdout)));
        }

        Ok(None)
    }

    fn generate_nautilus_signature(&self, verification: &VerificationMessage) -> Result<Vec<u8>> {
        // Create a payload to sign (this should match your verification format)
        let payload = format!(
            "{}:{}:{}:{}:{}",
            verification.user_wallet,
            verification.did_id,
            verification.result,
            verification.evidence_hash,
            verification.verified_at
        );
        
        // Sign the payload with the enclave keypair
        let signature = self.keypair.sign(payload.as_bytes());
        
        info!("Generated Nautilus signature for user: {}", verification.user_wallet);
        
        Ok(signature.as_ref().to_vec())
    }

    /// Parse ISO timestamp to milliseconds since epoch
    fn parse_timestamp_to_ms(&self, timestamp_str: &str) -> Result<u64> {
        let dt = DateTime::parse_from_rfc3339(&format!("{}Z", timestamp_str))
            .or_else(|_| {
                // Try parsing without timezone if the above fails
                let utc_str = if timestamp_str.ends_with('Z') {
                    timestamp_str.to_string()
                } else {
                    format!("{}Z", timestamp_str)
                };
                DateTime::parse_from_rfc3339(&utc_str)
            })
            .map_err(|e| anyhow!("Failed to parse timestamp '{}': {}", timestamp_str, e))?;
        
        let timestamp_ms = dt.timestamp_millis() as u64;
        info!("Converted timestamp '{}' to {} ms", timestamp_str, timestamp_ms);
        
        Ok(timestamp_ms)
    }

    async fn execute_update_verification_status(
        &self,
        user_address: &str,
        user_did_id: &str,
        verified: bool,
        nautilus_signature: Vec<u8>,
        signature_timestamp_ms: u64,  // When signature was created
        evidence_hash: &str,          // OCR hash from Python
    ) -> Result<()> {
        info!("Executing update_verification_status transaction...");
        info!("Signature timestamp: {}", signature_timestamp_ms);
        info!("Evidence hash: {}", evidence_hash);
        
        // Encode signature as base64 for CLI
        let signature_b64 = general_purpose::STANDARD.encode(&nautilus_signature);
        
        // Convert evidence hash to vector<u8> format for CLI
        let evidence_hash_bytes = hex::decode(evidence_hash)
            .map_err(|e| anyhow!("Failed to decode evidence hash: {}", e))?;
        let evidence_hash_b64 = general_purpose::STANDARD.encode(&evidence_hash_bytes);
        
        info!("Processing address: {}", user_address);
        
        // Execute sui client call command
        let output = Command::new("sui")
            .args([
                "client",
                "call",
                "--package", &self.package_id,
                "--module", "did_registry",
                "--function", "update_verification_status",
                "--args", 
                &self.registry_id,                    // registry
                &self.cap_id,                         // cap
                user_did_id,                          // user_did (the UserDID object ID we extracted)
                &verified.to_string(),                // verified
                &signature_b64,                       // nautilus_signature
                &signature_timestamp_ms.to_string(),  // signature_timestamp_ms
                &evidence_hash_b64,                   // evidence_hash
                &self.clock_id,                       // clock
                "--gas-budget", "10000000"
            ])
            .output()
            .map_err(|e| anyhow!("Failed to execute sui command: {}", e))?;

        // Process the output
        if output.status.success() {
            info!("update_verification_status executed successfully for user: {}", user_address);
            info!("Output: {}", String::from_utf8_lossy(&output.stdout));
            
            if !output.stderr.is_empty() {
                warn!("Warnings: {}", String::from_utf8_lossy(&output.stderr));
            }
        } else {
            error!("update_verification_status failed for user: {}", user_address);
            error!("Exit code: {}", output.status.code().unwrap_or(-1));
            error!("STDERR: {}", String::from_utf8_lossy(&output.stderr));
            error!("STDOUT: {}", String::from_utf8_lossy(&output.stdout));
            
            return Err(anyhow!("update_verification_status failed with exit code: {} - STDERR: {} - STDOUT: {}", 
                output.status.code().unwrap_or(-1),
                String::from_utf8_lossy(&output.stderr),
                String::from_utf8_lossy(&output.stdout)));
        }

        Ok(())
    }
}

/// Extract UserDID object ID from Sui transaction output
fn extract_user_did_id(output: &str) -> Option<String> {
    let lines: Vec<&str> = output.lines().collect();
    let mut i = 0;
    
    // Look for Created Objects section and find the UserDID object
    while i < lines.len() {
        let line = lines[i];
        
        // Look for ObjectID line
        if line.contains("ObjectID:") && line.contains("0x") {
            // Extract the object ID
            if let Some(start) = line.find("0x") {
                let id_part = &line[start..];
                let object_id = if let Some(end) = id_part.find(char::is_whitespace) {
                    &id_part[..end]
                } else {
                    id_part.trim()
                };
                
                // Look ahead for ObjectType line to check if this is a UserDID
                for j in (i+1)..(i+5).min(lines.len()) {
                    let next_line = lines[j];
                    if next_line.contains("ObjectType:") && next_line.contains("::did_registry::UserDID") {
                        info!("Found UserDID object: {}", object_id);
                        return Some(object_id.to_string());
                    }
                    // Stop looking if we hit another ObjectID (next object)
                    if next_line.contains("ObjectID:") {
                        break;
                    }
                }
            }
        }
        i += 1;
    }
    
    warn!("Could not find UserDID object in transaction output");
    None
}

// Function to start the Redis-Sui processor as a background task
pub async fn start_redis_sui_processor(keypair: Ed25519KeyPair) -> Result<()> {
    info!("Starting Redis-Sui processor...");
    
    let mut processor = RedisSuiProcessor::new(keypair)?;
    
    processor.start_processing().await
}
