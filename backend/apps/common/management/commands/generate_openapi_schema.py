"""
Management command to generate OpenAPI schema file.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
import yaml
import json
from pathlib import Path


class Command(BaseCommand):
    help = 'Generate OpenAPI schema file (YAML and JSON)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['yaml', 'json', 'both'],
            default='both',
            help='Output format (yaml, json, or both)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output directory (default: docs/api/)',
        )
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Validate schema after generation',
        )

    def handle(self, *args, **options):
        """Generate OpenAPI schema."""
        from drf_spectacular.generators import SchemaGenerator

        self.stdout.write('Generating OpenAPI schema...')

        # Get schema generator
        generator = SchemaGenerator()
        schema = generator.get_schema()

        # Determine output directory
        if options['output']:
            output_dir = Path(options['output'])
        else:
            # Default to docs/api/
            from django.conf import settings
            output_dir = settings.BASE_DIR.parent / 'docs' / 'api'

        # Create directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate YAML
        if options['format'] in ['yaml', 'both']:
            yaml_file = output_dir / 'openapi.yaml'
            self.stdout.write(f'Writing YAML schema to {yaml_file}...')

            with open(yaml_file, 'w') as f:
                yaml.dump(schema, f, default_flow_style=False, sort_keys=False)

            self.stdout.write(self.style.SUCCESS(f'✓ YAML schema generated: {yaml_file}'))

        # Generate JSON
        if options['format'] in ['json', 'both']:
            json_file = output_dir / 'openapi.json'
            self.stdout.write(f'Writing JSON schema to {json_file}...')

            with open(json_file, 'w') as f:
                json.dump(schema, f, indent=2)

            self.stdout.write(self.style.SUCCESS(f'✓ JSON schema generated: {json_file}'))

        # Validate schema if requested
        if options['validate']:
            self.stdout.write('\nValidating schema...')
            self.validate_schema(schema)

        self.stdout.write(self.style.SUCCESS('\n✓ Schema generation complete!'))

    def validate_schema(self, schema):
        """Validate OpenAPI schema."""
        errors = []

        # Check required fields
        required_fields = ['openapi', 'info', 'paths']
        for field in required_fields:
            if field not in schema:
                errors.append(f'Missing required field: {field}')

        # Check info section
        if 'info' in schema:
            info_required = ['title', 'version']
            for field in info_required:
                if field not in schema['info']:
                    errors.append(f'Missing required info field: {field}')

        # Check paths
        if 'paths' in schema:
            if not schema['paths']:
                errors.append('No API paths defined')
            else:
                self.stdout.write(f'  - Found {len(schema["paths"])} API paths')

        # Check components
        if 'components' in schema:
            if 'schemas' in schema['components']:
                self.stdout.write(
                    f'  - Found {len(schema["components"]["schemas"])} schemas'
                )

        # Report validation results
        if errors:
            self.stdout.write(self.style.ERROR('\n✗ Schema validation failed:'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('✓ Schema validation passed'))
