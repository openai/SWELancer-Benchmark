# fmt: off
# type: ignore
# ruff: noqa
# isort: skip_file

from datetime import datetime, timedelta, timezone

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


class CertificateAuthority:
    def __init__(self, common_name, country, state, locality, organization, key_size=4096):
        self.common_name = common_name
        self.country = country
        self.state = state
        self.locality = locality
        self.organization = organization
        self.key_size = key_size
        self.private_key = None
        self.certificate = None

    def generate_private_key(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
        )
        return self.private_key

    def create_self_signed_cert(self, valid_days=3650):
        if not self.private_key:
            self.generate_private_key()

        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, self.country),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, self.state),
                x509.NameAttribute(NameOID.LOCALITY_NAME, self.locality),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, self.organization),
                x509.NameAttribute(NameOID.COMMON_NAME, self.common_name),
            ]
        )

        self.certificate = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=valid_days))
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    key_cert_sign=True,
                    crl_sign=True,
                    digital_signature=False,
                    key_encipherment=False,
                    key_agreement=False,
                    data_encipherment=False,
                    content_commitment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(self.private_key, hashes.SHA256())
        )
        return self.certificate

    def save_private_key(self, filepath, password=None):
        if not self.private_key:
            raise ValueError("Private key not generated.")
        encryption = (
            serialization.BestAvailableEncryption(password.encode())
            if password
            else serialization.NoEncryption()
        )
        with open(filepath, "wb") as f:
            f.write(
                self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=encryption,
                )
            )

    def get_certificate_pem(self) -> bytes:
        if not self.certificate:
            raise ValueError("Certificate not created.")
        return self.certificate.public_bytes(
            encoding=serialization.Encoding.PEM,
        )

    def issue_certificate(
        self, subject_details, root_domain, san_list=None, valid_days=825, key_size=2048
    ):
        # Generate server private key
        server_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )

        # Build CSR
        subject = x509.Name(
            [
                x509.NameAttribute(NameOID.COUNTRY_NAME, subject_details.get("C", "US")),
                x509.NameAttribute(
                    NameOID.STATE_OR_PROVINCE_NAME, subject_details.get("ST", "State")
                ),
                x509.NameAttribute(NameOID.LOCALITY_NAME, subject_details.get("L", "City")),
                x509.NameAttribute(
                    NameOID.ORGANIZATION_NAME, subject_details.get("O", "Organization")
                ),
                x509.NameAttribute(
                    NameOID.COMMON_NAME, subject_details.get("CN", f"*.{root_domain}")
                ),  # Wildcard CN
            ]
        )

        csr_builder = x509.CertificateSigningRequestBuilder().subject_name(subject)

        if san_list:
            san = x509.SubjectAlternativeName([x509.DNSName(name) for name in san_list])
            csr_builder = csr_builder.add_extension(san, critical=False)

        csr = csr_builder.sign(server_private_key, hashes.SHA256())

        # Build Certificate
        certificate = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(self.certificate.subject)
            .public_key(csr.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=valid_days))
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                csr.extensions.get_extension_for_class(x509.SubjectAlternativeName).value,
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [
                        ExtendedKeyUsageOID.SERVER_AUTH,
                    ]
                ),
                critical=False,
            )
            .sign(self.private_key, hashes.SHA256())
        )

        return server_private_key, certificate


def make_certs(root_domain: str) -> tuple[bytes, bytes, bytes]:
    # Initialize CA
    ca = CertificateAuthority(
        common_name=root_domain,
        country="US",
        state="California",
        locality="San Francisco",
        organization="OpenAI Internal Alcatraz",
    )

    # Create CA certificate
    _ca_cert = ca.create_self_signed_cert()

    # Save CA private key and certificate
    # ca.save_private_key("ca_private_key.pem")
    ca_certificate_pem = ca.get_certificate_pem()

    # Details for the wildcard server certificate
    server_details = {
        "C": "US",
        "ST": "California",
        "L": "San Francisco",
        "O": "OpenAI Internal Alcatraz",
        "CN": f"*.{root_domain}",  # Wildcard CN
    }
    san = [f"*.{root_domain}", root_domain]  # SAN includes wildcard and base domain

    # Issue server certificate
    server_key, server_cert = ca.issue_certificate(
        subject_details=server_details,
        root_domain=root_domain,
        san_list=san,
    )

    # Save server private key and certificate
    server_private_key_pem = server_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    server_certificate_pem = server_cert.public_bytes(
        encoding=serialization.Encoding.PEM,
    )

    return server_private_key_pem, server_certificate_pem, ca_certificate_pem
