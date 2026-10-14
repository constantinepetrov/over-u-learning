#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
	echo "Usage: $0 <artifact-directory> <IAP-private-key> <output-OCI-tar>" >&2
	exit 2
fi

artifact_dir="$1"
private_key="$2"
output_tar="$3"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/overu-image-decrypt.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT
umask 077

cp "$private_key" "$tmp_dir/iap-key"
ssh-keygen -p -m PEM -P "" -N "" -f "$tmp_dir/iap-key" >/dev/null
openssl pkeyutl -decrypt -inkey "$tmp_dir/iap-key" \
	-in "$artifact_dir/overu-production-image.key.enc" \
	-out "$tmp_dir/key-material" \
	-pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 \
	-pkeyopt rsa_mgf1_md:sha256

enc_key="$(head -c 64 "$tmp_dir/key-material")"
mac_key="$(tail -c 64 "$tmp_dir/key-material")"
test "${#enc_key}" -eq 64
test "${#mac_key}" -eq 64

openssl dgst -sha256 -mac HMAC -macopt "hexkey:$mac_key" -binary \
	"$artifact_dir/overu-production-image.oci.tar.enc" > "$tmp_dir/actual.hmac"
cmp -s "$tmp_dir/actual.hmac" "$artifact_dir/overu-production-image.hmac"

printf '%s' "$enc_key" > "$tmp_dir/encryption-passphrase"
openssl enc -d -aes-256-cbc -salt -pbkdf2 -iter 600000 -md sha256 \
	-in "$artifact_dir/overu-production-image.oci.tar.enc" \
	-out "$output_tar" -pass "file:$tmp_dir/encryption-passphrase"

expected_sha="$(sed -n 's/^oci_archive_sha256=//p' "$artifact_dir/overu-production-image.manifest")"
actual_sha="$(shasum -a 256 "$output_tar" | awk '{print $1}')"
test "$actual_sha" = "$expected_sha"
printf 'Verified OCI archive SHA-256: %s\n' "$actual_sha"
