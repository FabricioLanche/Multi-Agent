#!/usr/bin/env python3
"""
create_s3_bucket_for_tareas.py

Script enfocado en la creación/configuración del bucket S3 para subir imágenes de Tareas
y utilidades para obtener URLs pre-firmadas (PUT/GET) o subir archivos desde máquina local.

Comportamiento por defecto:
- Crea un bucket llamado S3_BUCKET_TAREAS (variable de entorno) o "tareas-imagenes-{aws_account_id}"
- Mantiene el bucket privado y recomienda uso de URLs pre-firmadas para uploads/descargas.
- Opcional: si S3_PUBLIC_READ=true en .env, configura política pública (no recomendado para producción).
- Actualiza .env (../.env) con S3_BUCKET_TAREAS y AWS_ACCOUNT_ID si es necesario.

Uso:
  python create_s3_bucket_for_tareas.py create-bucket
  python create_s3_bucket_for_tareas.py presign-put --key tareas/<id>.jpg --expires 600
  python create_s3_bucket_for_tareas.py presign-get --key tareas/<id>.jpg --expires 600
  python create_s3_bucket_for_tareas.py upload-file --key tareas/<id>.jpg --file ./mi.jpg --public-read

Requiere: boto3, python-dotenv
"""
import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_PUBLIC_READ = os.getenv("S3_PUBLIC_READ", "false").lower() in ("1", "true", "yes")
ENV_PATH = Path(__file__).parent.parent / ".env"  # ../.env (igual que tu script anterior)

s3 = boto3.client("s3", region_name=AWS_REGION)
sts = boto3.client("sts", region_name=AWS_REGION)


def get_aws_account_id() -> str:
    account = os.getenv("AWS_ACCOUNT_ID")
    if account:
        return account
    try:
        account = sts.get_caller_identity()["Account"]
        print(f"ℹ️  AWS Account ID detectado: {account}")
        return account
    except Exception as e:
        print(f"❌ No fue posible obtener AWS Account ID: {e}")
        raise


def bucket_name_for_account(account_id: str) -> str:
    return os.getenv("S3_BUCKET_TAREAS", f"tareas-imagenes-{account_id}")


def create_bucket(bucket_name: str) -> bool:
    """Crea bucket y aplica configuraciones mínimas (privacidad por defecto)."""
    region = AWS_REGION
    try:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        print(f"✅ Bucket {bucket_name} creado")
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code == "BucketAlreadyOwnedByYou":
            print(f"✅ Bucket {bucket_name} ya existe y es tuyo")
        elif code == "BucketAlreadyExists":
            print(f"⚠️  Bucket {bucket_name} ya existe (posiblemente otra cuenta).")
            return False
        else:
            print(f"❌ Error creando bucket: {e}")
            return False

    # Por seguridad, bloquear acceso público por defecto
    try:
        s3.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        print("🔐 Block Public Access configurado (recomendado)")
    except Exception as e:
        print(f"⚠️  No se pudo configurar Block Public Access: {e}")

    # Ownership Controls (BucketOwnerPreferred)
    try:
        s3.put_bucket_ownership_controls(
            Bucket=bucket_name,
            OwnershipControls={"Rules": [{"ObjectOwnership": "BucketOwnerPreferred"}]},
        )
        print("✅ Ownership Controls configurado")
    except Exception as e:
        print(f"⚠️  No se pudo configurar Ownership Controls: {e}")

    # CORS: permitir PUT desde browser si se usa presigned POST/PUT directamente
    try:
        cors = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["GET", "PUT", "POST", "OPTIONS"],
                    "AllowedOrigins": [os.getenv("S3_ALLOWED_ORIGINS", "*")],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3000,
                }
            ]
        }
        s3.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors)
        print("✅ CORS configurado")
    except Exception as e:
        print(f"⚠️  No se pudo configurar CORS: {e}")

    # Si se pidió lectura pública explícita (no recomendado), aplicar política
    if S3_PUBLIC_READ:
        try:
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{bucket_name}/*"],
                    }
                ],
            }
            s3.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
            print("⚠️  Política pública aplicada (S3_PUBLIC_READ=true)")
        except Exception as e:
            print(f"⚠️  No se pudo aplicar política pública: {e}")

    # Actualizar .env con S3_BUCKET_TAREAS y AWS_ACCOUNT_ID
    try:
        account_id = get_aws_account_id()
        update_env_vars({"S3_BUCKET_TAREAS": bucket_name, "AWS_ACCOUNT_ID": account_id})
    except Exception:
        pass

    return True


def update_env_vars(kv: dict):
    """Actualiza (o crea) variables en ../.env"""
    env_path = ENV_PATH
    lines = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    kv_existing = {k: False for k in kv.keys()}
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0]
        if key in kv:
            new_lines.append(f"{key}={kv[key]}")
            kv_existing[key] = True
        else:
            new_lines.append(line)
    for k, added in kv_existing.items():
        if not added:
            new_lines.append(f"{k}={kv[k]}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"✅ .env actualizado en: {env_path}")


def generate_presigned_put_url(bucket_name: str, key: str, expires_in: int = 600) -> str:
    """Genera una URL pre-firmada para PUT (subir objeto)."""
    try:
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as e:
        print(f"❌ Error generando presigned PUT URL: {e}")
        raise


def generate_presigned_get_url(bucket_name: str, key: str, expires_in: int = 600) -> str:
    """Genera una URL pre-firmada para GET (descargar objeto)."""
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except Exception as e:
        print(f"❌ Error generando presigned GET URL: {e}")
        raise


def upload_file_local(bucket_name: str, key: str, file_path: Path, public_read: bool = False) -> bool:
    """Sube un archivo desde el filesystem al bucket. Opcionalmente marca public-read."""
    extra_args = {}
    if public_read:
        extra_args["ACL"] = "public-read"
    try:
        s3.upload_file(str(file_path), bucket_name, key, ExtraArgs=extra_args or None)
        print(f"✅ Archivo subido: s3://{bucket_name}/{key}")
        return True
    except Exception as e:
        print(f"❌ Error subiendo archivo: {e}")
        return False


def parse_args():
    p = argparse.ArgumentParser(description="Configurar bucket S3 para imágenes de tareas y utilidades.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.create_parser = sub.add_parser("create-bucket", help="Crear y configurar el bucket S3 para tareas")

    presign_put = sub.add_parser("presign-put", help="Generar URL pre-firmada para subir (PUT)")
    presign_put.add_argument("--key", required=True, help="Key S3 (ej: tareas/123.jpg)")
    presign_put.add_argument("--expires", type=int, default=600, help="Segundos de expiración")

    presign_get = sub.add_parser("presign-get", help="Generar URL pre-firmada para descargar (GET)")
    presign_get.add_argument("--key", required=True, help="Key S3 (ej: tareas/123.jpg)")
    presign_get.add_argument("--expires", type=int, default=600, help="Segundos de expiración")

    upload = sub.add_parser("upload-file", help="Subir archivo local al bucket")
    upload.add_argument("--key", required=True, help="Key destino en S3 (ej: tareas/123.jpg)")
    upload.add_argument("--file", required=True, help="Path del archivo local")
    upload.add_argument("--public-read", action="store_true", help="Establecer ACL public-read (no recomendado)")

    return p.parse_args()


def main():
    args = parse_args()
    try:
        account = get_aws_account_id()
    except Exception:
        print("❌ No se puede continuar sin AWS Account ID")
        return

    bucket = bucket_name_for_account(account)

    if args.cmd == "create-bucket":
        ok = create_bucket(bucket)
        if ok:
            print("🎉 Bucket configurado correctamente")
        else:
            print("⚠️  Hubo problemas configurando el bucket")
        return

    if args.cmd == "presign-put":
        url = generate_presigned_put_url(bucket, args.key, expires_in=args.expires)
        print(url)
        return

    if args.cmd == "presign-get":
        url = generate_presigned_get_url(bucket, args.key, expires_in=args.expires)
        print(url)
        return

    if args.cmd == "upload-file":
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Archivo no encontrado: {file_path}")
            return
        ok = upload_file_local(bucket, args.key, file_path, public_read=args.public_read)
        if ok:
            if args.public_read:
                print(f"🔗 URL pública: https://{bucket}.s3.amazonaws.com/{args.key}")
            else:
                print("🔒 Archivo subido en modo privado. Use presigned-get para descargar.")
        return


if __name__ == "__main__":
    main()