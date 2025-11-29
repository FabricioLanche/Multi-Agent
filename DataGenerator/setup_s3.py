#!/usr/bin/env python3
import boto3
import os
import json
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

s3 = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
sts = boto3.client('sts', region_name=os.getenv('AWS_REGION', 'us-east-1'))

# Obtener AWS Account ID si no está en .env
aws_account_id = os.getenv('AWS_ACCOUNT_ID')
if not aws_account_id:
    try:
        aws_account_id = sts.get_caller_identity()['Account']
        print(f'ℹ️  AWS Account ID detectado: {aws_account_id}')
    except Exception as e:
        print(f'❌ Error al obtener AWS Account ID: {e}')
        exit(1)

# Usar formato consistente con serverless.yml
bucket_name = f"recetas-medicas-data-{aws_account_id}"
region = os.getenv('AWS_REGION', 'us-east-1')

print(f"🪣 Configurando bucket S3: {bucket_name}")

# Intentar crear el bucket
try:
    if region == 'us-east-1':
        s3.create_bucket(Bucket=bucket_name)
    else:
        s3.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={'LocationConstraint': region}
        )
    print(f'✅ Bucket {bucket_name} creado exitosamente')
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'BucketAlreadyOwnedByYou':
        print(f'✅ Bucket {bucket_name} ya existe y es tuyo')
    elif error_code == 'BucketAlreadyExists':
        print(f'⚠️  Bucket {bucket_name} ya existe pero no es accesible')
        print(f'ℹ️  El bucket ya fue creado previamente o está siendo usado')
    else:
        print(f'❌ Error al crear bucket: {e}')
        exit(1)

# Deshabilitar Block Public Access
try:
    print('🔓 Configurando acceso público...')
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': False,
            'IgnorePublicAcls': False,
            'BlockPublicPolicy': False,
            'RestrictPublicBuckets': False
        }
    )
    print('✅ Block Public Access deshabilitado')
except Exception as e:
    print(f'⚠️  Advertencia al configurar Block Public Access: {e}')

# Configurar Ownership Controls
try:
    s3.put_bucket_ownership_controls(
        Bucket=bucket_name,
        OwnershipControls={
            'Rules': [
                {
                    'ObjectOwnership': 'BucketOwnerPreferred'
                }
            ]
        }
    )
    print('✅ Ownership Controls configurado')
except Exception as e:
    print(f'⚠️  Advertencia al configurar Ownership Controls: {e}')

# Configurar política de bucket para acceso público de lectura
try:
    bucket_policy = {
        'Version': '2012-10-17',
        'Statement': [{
            'Sid': 'PublicReadGetObject',
            'Effect': 'Allow',
            'Principal': '*',
            'Action': 's3:GetObject',
            'Resource': f'arn:aws:s3:::{bucket_name}/*'
        }]
    }
    
    s3.put_bucket_policy(
        Bucket=bucket_name,
        Policy=json.dumps(bucket_policy)
    )
    print('✅ Política de bucket configurada para acceso público de lectura')
except Exception as e:
    print(f'⚠️  Advertencia al configurar política de bucket: {e}')

# Configurar CORS
try:
    cors_configuration = {
        'CORSRules': [{
            'AllowedHeaders': ['*'],
            'AllowedMethods': ['GET', 'PUT', 'POST'],
            'AllowedOrigins': ['*'],
            'MaxAgeSeconds': 3000
        }]
    }
    
    s3.put_bucket_cors(
        Bucket=bucket_name,
        CORSConfiguration=cors_configuration
    )
    print('✅ CORS configurado')
except Exception as e:
    print(f'⚠️  Advertencia al configurar CORS: {e}')

# Actualizar .env con el bucket name correcto
env_path = os.path.join('..', '.env')
if os.path.exists(env_path):
    try:
        with open(env_path, 'r') as f:
            lines = f.readlines()
        
        bucket_line_found = False
        account_line_found = False
        
        with open(env_path, 'w') as f:
            for line in lines:
                if line.startswith('S3_BUCKET_RECETAS='):
                    f.write(f'S3_BUCKET_RECETAS={bucket_name}\n')
                    bucket_line_found = True
                elif line.startswith('AWS_ACCOUNT_ID='):
                    f.write(f'AWS_ACCOUNT_ID={aws_account_id}\n')
                    account_line_found = True
                else:
                    f.write(line)
            
            # Agregar si no existían
            if not bucket_line_found:
                f.write(f'S3_BUCKET_RECETAS={bucket_name}\n')
            if not account_line_found:
                f.write(f'AWS_ACCOUNT_ID={aws_account_id}\n')
        
        print(f'✅ Archivo .env actualizado')
    except Exception as e:
        print(f'⚠️  Advertencia al actualizar .env: {e}')

print('\n🎉 Configuración de S3 completada')
print(f'📝 Bucket name: {bucket_name}')
print(f'🌍 Región: {region}')
print(f'🔗 URL base: https://{bucket_name}.s3.amazonaws.com/')