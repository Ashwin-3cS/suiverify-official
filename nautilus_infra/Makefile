REGISTRY := local
.DEFAULT_GOAL :=
.PHONY: default
default: out/enclaveos.tar

out:
	mkdir out

out/enclaveos.tar: out \
	$(shell git ls-files \
		src/init \
		src/aws \
		src/verification-server \
	) \
	$(shell find ../verification-backend -type f -name '*.py' -o -name '*.txt' -o -name '.env*')
	docker build \
		--tag $(REGISTRY)/enclaveos \
		--progress=plain \
		--platform linux/amd64 \
		--output type=local,rewrite-timestamp=true,dest=out\
		-f Containerfile \
		.

.PHONY: run
run: out/nitro.eif
	sudo nitro-cli \
		run-enclave \
		--cpu-count 6 \
		--memory 26624 \
		--eif-path out/nitro.eif
	@echo "Enclave running with integrated services:"
	@echo "  - Rust verification-server (internal port 4000)"
	@echo "  - Python verification service (main port 8000)"
	@echo "  - Access via: vsock-proxy 8000 localhost 8000"

.PHONY: run-debug
run-debug: out/nitro.eif
	sudo nitro-cli \
		run-enclave \
		--cpu-count 6 \
		--memory 26624 \
		--eif-path out/nitro.eif \
		--debug-mode \
		--attach-console

.PHONY: run-local
run-local:
	@echo "Running services locally for development..."
	cd ../verification-backend && python3 main.py &
	cd src/verification-server && cargo run &
	@echo "Services started:"
	@echo "  - Python service: http://localhost:8000"
	@echo "  - Rust service: http://localhost:4000"
	@echo "Use 'make stop-local' to stop services"

.PHONY: stop-local
stop-local:
	@echo "Stopping local services..."
	pkill -f "python3 main.py" || true
	pkill -f "verification-server" || true
	@echo "Local services stopped"

.PHONY: update
update:
	./update.sh

.PHONY: check-config
check-config:
	@echo "=== CURRENT SYSTEM CONFIG ==="
	@echo "Total CPUs: $$(nproc)"
	@echo "Total Memory: $$(free -h | grep '^Mem:' | awk '{print $$2}')"
	@echo "=== ENCLAVE ALLOCATOR CONFIG ==="
	@cat /etc/nitro_enclaves/allocator.yaml
	@echo "=== RUNNING ENCLAVES ==="
	@sudo nitro-cli describe-enclaves || echo "No enclaves running"

.PHONY: stop
stop:
	sudo nitro-cli terminate-enclave --all

.PHONY: logs
logs:
	sudo nitro-cli console --enclave-name $(shell sudo nitro-cli describe-enclaves | jq -r '.[0].EnclaveID')

.PHONY: status
status:
	@echo "=== ENCLAVE STATUS ==="
	sudo nitro-cli describe-enclaves || echo "No enclaves running"
	@echo "=== LOCAL SERVICES STATUS ==="
	ps aux | grep -E "(python3 main.py|verification-server)" | grep -v grep || echo "No local services running"
