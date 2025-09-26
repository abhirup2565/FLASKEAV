#!/usr/bin/env python3
"""
Database Configuration Exporter for Port Management System
Extracts and displays the current configuration of all models in the system
"""

import os
import sys
from datetime import datetime
import json
from collections import defaultdict

# Add project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import *

def get_system_overview():
    """Get high-level system statistics"""
    with app.app_context():
        overview = {
            'applications': Application.query.filter_by(is_active=True).count(),
            'modules': Module.query.filter_by(is_active=True).count(),
            'entity_types': EntityType.query.filter_by(is_active=True).count(),
            'total_attributes': AttributeDefinition.query.filter_by(is_active=True).count(),
            'total_forms': FormDefinition.query.filter_by(is_active=True).count(),
            'total_instances': EntityInstance.query.filter_by(is_active=True).count(),
            'users': User.query.filter_by(is_active=True).count(),
            'roles': Role.query.filter_by(is_active=True).count()
        }
        return overview

def get_applications_config():
    """Get all applications and their modules"""
    with app.app_context():
        apps_config = []
        applications = Application.query.filter_by(is_active=True).order_by(Application.order_index, Application.name).all()
        
        for application in applications:
            modules_list = []
            modules = application.modules.filter_by(is_active=True).order_by(Module.order_index, Module.name).all()
            
            for module in modules:
                entity_types_count = module.entity_types.filter_by(is_active=True).count()
                modules_list.append({
                    'id': module.id,
                    'code': module.code,
                    'name': module.name,
                    'description': module.description,
                    'icon': module.icon,
                    'order_index': module.order_index,
                    'is_system': module.is_system,
                    'entity_types_count': entity_types_count,
                    'created_at': module.created_at.isoformat() if module.created_at else None
                })
            
            apps_config.append({
                'id': application.id,
                'code': application.code,
                'name': application.name,
                'description': application.description,
                'icon': application.icon,
                'order_index': application.order_index,
                'created_at': application.created_at.isoformat() if application.created_at else None,
                'modules': modules_list
            })
        
        return apps_config

def get_entity_types_config():
    """Get detailed configuration of all entity types"""
    with app.app_context():
        entities_config = []
        entity_types = EntityType.query.filter_by(is_active=True).order_by(EntityType.module_id, EntityType.order_index).all()
        
        for entity in entity_types:
            # Get attributes
            attributes_list = []
            attributes = entity.attribute_definitions.filter_by(is_active=True).order_by(AttributeDefinition.order_index).all()
            
            for attr in attributes:
                attributes_list.append({
                    'id': attr.id,
                    'code': attr.code,
                    'name': attr.name,
                    'description': attr.description,
                    'data_type': attr.data_type.value,
                    'max_length': attr.max_length,
                    'decimal_precision': attr.decimal_precision,
                    'decimal_scale': attr.decimal_scale,
                    'default_value': attr.default_value,
                    'is_required': attr.is_required,
                    'is_unique': attr.is_unique,
                    'is_indexed': attr.is_indexed,
                    'validation_rules': attr.validation_rules,
                    'order_index': attr.order_index
                })
            
            # Get forms
            forms_list = []
            forms = entity.form_definitions.filter_by(is_active=True).all()
            
            for form in forms:
                # Get form fields
                form_fields = []
                fields = form.form_field_configurations.filter_by().order_by(FormFieldConfiguration.order_index).all()
                
                for field in fields:
                    # Get dropdown connection details
                    dropdown_info = None
                    if field.dropdown_source_entity_id and field.dropdown_source_attribute_id:
                        source_entity = EntityType.query.get(field.dropdown_source_entity_id)
                        source_attr = AttributeDefinition.query.get(field.dropdown_source_attribute_id)
                        display_attr = None
                        if field.dropdown_display_attribute_id:
                            display_attr = AttributeDefinition.query.get(field.dropdown_display_attribute_id)
                        
                        dropdown_info = {
                            'source_entity_name': source_entity.name if source_entity else None,
                            'source_entity_code': source_entity.code if source_entity else None,
                            'source_attribute_name': source_attr.name if source_attr else None,
                            'source_attribute_code': source_attr.code if source_attr else None,
                            'display_attribute_name': display_attr.name if display_attr else None,
                            'display_attribute_code': display_attr.code if display_attr else None,
                            'unique_values_only': field.show_unique_values_only
                        }
                    
                    form_fields.append({
                        'attribute_code': field.attribute_definition.code,
                        'field_label': field.field_label,
                        'field_type': field.field_type.value,
                        'order_index': field.order_index,
                        'is_visible': field.is_visible,
                        'is_editable': field.is_editable,
                        'is_required': field.is_required,
                        'dropdown_source_entity_id': field.dropdown_source_entity_id,
                        'dropdown_source_attribute_id': field.dropdown_source_attribute_id,
                        'show_unique_values_only': field.show_unique_values_only,
                        'placeholder_text': field.placeholder_text,
                        'help_text': field.help_text,
                        'dropdown_connection': dropdown_info
                    })
                
                forms_list.append({
                    'id': form.id,
                    'code': form.code,
                    'name': form.name,
                    'form_type': form.form_type.value,
                    'layout_type': form.layout_type.value,
                    'records_per_page': form.records_per_page,
                    'is_default': form.is_default,
                    'fields': form_fields
                })
            
            # Get instance count
            instance_count = entity.entity_instances.filter_by(is_active=True).count()
            
            entities_config.append({
                'id': entity.id,
                'module_code': entity.module.code,
                'module_name': entity.module.name,
                'application_name': entity.module.application.name,
                'code': entity.code,
                'name': entity.name,
                'description': entity.description,
                'table_name': entity.table_name,
                'is_master': entity.is_master,
                'is_transactional': entity.is_transactional,
                'icon': entity.icon,
                'order_index': entity.order_index,
                'instance_count': instance_count,
                'attributes': attributes_list,
                'forms': forms_list,
                'created_at': entity.created_at.isoformat() if entity.created_at else None
            })
        
        return entities_config

def get_users_and_roles_config():
    """Get users and roles configuration"""
    with app.app_context():
        # Get roles
        roles_list = []
        roles = Role.query.filter_by(is_active=True).order_by(Role.name).all()
        
        for role in roles:
            user_count = role.user_roles.count()
            permissions_count = role.entity_permissions.count()
            
            roles_list.append({
                'id': role.id,
                'code': role.code,
                'name': role.name,
                'description': role.description,
                'is_system': role.is_system,
                'user_count': user_count,
                'permissions_count': permissions_count,
                'created_at': role.created_at.isoformat() if role.created_at else None
            })
        
        # Get users
        users_list = []
        users = User.query.filter_by(is_active=True).order_by(User.username).all()
        
        for user in users:
            user_roles = [ur.role.name for ur in user.user_roles]
            favorite_modules = [fm.module.name for fm in user.favorite_modules]
            
            users_list.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'roles': user_roles,
                'favorite_modules': favorite_modules,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'created_at': user.created_at.isoformat() if user.created_at else None
            })
        
        return {
            'roles': roles_list,
            'users': users_list
        }

def get_sample_data():
    """Get sample of actual data from each entity type"""
    with app.app_context():
        sample_data = {}
        entity_types = EntityType.query.filter_by(is_active=True).limit(10).all()
        
        for entity in entity_types:
            # Get up to 5 sample instances
            instances = entity.entity_instances.filter_by(is_active=True).limit(5).all()
            
            if instances:
                entity_samples = []
                attributes = entity.attribute_definitions.filter_by(is_active=True).order_by(AttributeDefinition.order_index).all()
                
                for instance in instances:
                    instance_data = {
                        'id': instance.id,
                        'instance_code': instance.instance_code,
                        'workflow_status': instance.workflow_status,
                        'created_at': instance.created_at.isoformat() if instance.created_at else None,
                        'attributes': {}
                    }
                    
                    # Get attribute values
                    for attr in attributes[:10]:  # Limit to first 10 attributes
                        value = instance.get_attribute_value(attr.code)
                        if value is not None:
                            if hasattr(value, 'isoformat'):  # datetime
                                value = value.isoformat()
                            instance_data['attributes'][attr.code] = value
                    
                    entity_samples.append(instance_data)
                
                sample_data[entity.code] = {
                    'entity_name': entity.name,
                    'sample_count': len(entity_samples),
                    'total_count': entity.entity_instances.filter_by(is_active=True).count(),
                    'samples': entity_samples
                }
        
        return sample_data

def analyze_dropdown_connections(entities_config):
    """Analyze and return dropdown connections"""
    dropdown_connections = []
    for entity in entities_config:
        for form in entity['forms']:
            for field in form['fields']:
                if field.get('dropdown_connection'):
                    conn = field['dropdown_connection']
                    dropdown_connections.append({
                        'target_entity': entity['name'],
                        'target_attribute': field['attribute_code'],
                        'form_type': form['form_type'],
                        'source_entity': conn['source_entity_name'],
                        'source_attribute': conn['source_attribute_name'],
                        'display_attribute': conn['display_attribute_name'],
                        'unique_only': conn['unique_values_only']
                    })
    return dropdown_connections

def format_configuration_report():
    """Generate a comprehensive configuration report"""
    print("=" * 80)
    print("PORT MANAGEMENT SYSTEM - CONFIGURATION REPORT")
    print("=" * 80)
    print(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # System Overview
    print("SYSTEM OVERVIEW")
    print("-" * 40)
    overview = get_system_overview()
    for key, value in overview.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    print()
    
    # Applications and Modules
    print("APPLICATIONS & MODULES")
    print("-" * 40)
    apps_config = get_applications_config()
    for application_data in apps_config:
        print(f"\nApplication: {application_data['name']} ({application_data['code']})")
        if application_data['description']:
            print(f"  Description: {application_data['description']}")
        print(f"  Modules: {len(application_data['modules'])}")
        
        for module in application_data['modules']:
            print(f"    - {module['name']} ({module['code']})")
            print(f"      Entity Types: {module['entity_types_count']}")
            if module['description']:
                print(f"      Description: {module['description']}")
    
    print("\n" + "=" * 80)
    
    # Entity Types Configuration
    print("ENTITY TYPES CONFIGURATION")
    print("-" * 40)
    entities_config = get_entity_types_config()
    
    for entity in entities_config:
        print(f"\nEntity: {entity['name']} ({entity['code']})")
        print(f"  Module: {entity['application_name']} > {entity['module_name']}")
        print(f"  Type: {'Master' if entity['is_master'] else ''}{'Transactional' if entity['is_transactional'] else ''}")
        print(f"  Records: {entity['instance_count']}")
        print(f"  Attributes: {len(entity['attributes'])}")
        print(f"  Forms: {len(entity['forms'])}")
        
        if entity['description']:
            print(f"  Description: {entity['description']}")
        
        # Show attributes
        print(f"  \nAttributes:")
        for attr in entity['attributes']:
            required_str = " (Required)" if attr['is_required'] else ""
            unique_str = " (Unique)" if attr['is_unique'] else ""
            length_str = f" (Max: {attr['max_length']})" if attr['max_length'] else ""
            print(f"    - {attr['name']} ({attr['code']}) - {attr['data_type']}{length_str}{required_str}{unique_str}")
        
        # Show forms
        print(f"  \nForms:")
        for form in entity['forms']:
            default_str = " (Default)" if form['is_default'] else ""
            print(f"    - {form['name']} ({form['form_type']}){default_str}")
            print(f"      Fields: {len(form['fields'])}")
            
            # Show dropdown connections for this form
            dropdown_fields = [f for f in form['fields'] if f.get('dropdown_connection')]
            if dropdown_fields:
                print(f"      Dropdown Connections:")
                for field in dropdown_fields:
                    conn = field['dropdown_connection']
                    unique_str = " (unique values)" if conn['unique_values_only'] else ""
                    display_info = f" → {conn['display_attribute_name']}" if conn['display_attribute_name'] and conn['display_attribute_name'] != conn['source_attribute_name'] else ""
                    print(f"        * {field['attribute_code']} → {conn['source_entity_name']}.{conn['source_attribute_name']}{display_info}{unique_str}")
    
    print("\n" + "=" * 80)
    
    # Dropdown Connections Analysis
    print("DROPDOWN CONNECTIONS & RELATIONSHIPS")
    print("-" * 40)
    
    dropdown_connections = analyze_dropdown_connections(entities_config)
    
    if dropdown_connections:
        # Group by target entity
        connections_by_entity = defaultdict(list)
        for conn in dropdown_connections:
            connections_by_entity[conn['target_entity']].append(conn)
        
        for entity_name, connections in connections_by_entity.items():
            print(f"\n{entity_name}:")
            for conn in connections:
                unique_str = " (unique values)" if conn['unique_only'] else ""
                display_info = f" → {conn['display_attribute']}" if conn['display_attribute'] and conn['display_attribute'] != conn['source_attribute'] else ""
                print(f"  {conn['target_attribute']} ({conn['form_type']}) ← {conn['source_entity']}.{conn['source_attribute']}{display_info}{unique_str}")
        
        # Summary of all connections
        print(f"\nSummary:")
        print(f"  Total dropdown connections: {len(dropdown_connections)}")
        source_entities = set(conn['source_entity'] for conn in dropdown_connections)
        target_entities = set(conn['target_entity'] for conn in dropdown_connections)
        print(f"  Source entities: {', '.join(sorted(source_entities))}")
        print(f"  Target entities: {', '.join(sorted(target_entities))}")
    else:
        print("No dropdown connections configured in the system.")
    
    print("\n" + "=" * 80)
    
    # Users and Roles
    print("USERS & ROLES")
    print("-" * 40)
    users_roles = get_users_and_roles_config()
    
    print(f"Roles ({len(users_roles['roles'])}):")
    for role in users_roles['roles']:
        system_str = " (System)" if role['is_system'] else ""
        print(f"  - {role['name']} ({role['code']}){system_str}")
        print(f"    Users: {role['user_count']}, Permissions: {role['permissions_count']}")
    
    print(f"\nUsers ({len(users_roles['users'])}):")
    for user in users_roles['users']:
        print(f"  - {user['username']} ({user['full_name']})")
        print(f"    Email: {user['email']}")
        print(f"    Roles: {', '.join(user['roles'])}")
        if user['favorite_modules']:
            print(f"    Favorites: {', '.join(user['favorite_modules'])}")
        if user['last_login']:
            print(f"    Last Login: {user['last_login']}")
    
    print("\n" + "=" * 80)
    
    # Sample Data
    print("SAMPLE DATA")
    print("-" * 40)
    sample_data = get_sample_data()
    
    for entity_code, data in sample_data.items():
        print(f"\n{data['entity_name']} ({entity_code}):")
        print(f"  Total Records: {data['total_count']}")
        print(f"  Sample Records: {data['sample_count']}")
        
        for i, sample in enumerate(data['samples'], 1):
            print(f"    Record {i}:")
            if sample['instance_code']:
                print(f"      Code: {sample['instance_code']}")
            for attr_code, value in sample['attributes'].items():
                if len(str(value)) > 50:
                    value = str(value)[:47] + "..."
                print(f"      {attr_code}: {value}")
    
    print("\n" + "=" * 80)
    print("END OF CONFIGURATION REPORT")
    print("=" * 80)

def export_json_config():
    """Export configuration as JSON"""
    config_data = {
        'generated_at': datetime.now().isoformat(),
        'system_overview': get_system_overview(),
        'applications': get_applications_config(),
        'entity_types': get_entity_types_config(),
        'users_and_roles': get_users_and_roles_config(),
        'sample_data': get_sample_data()
    }
    
    # Add dropdown connections analysis
    entities_config = get_entity_types_config()
    config_data['dropdown_connections'] = analyze_dropdown_connections(entities_config)
    
    filename = f"port_management_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nConfiguration exported to: {filename}")
    return filename

def main():
    """Main function to run the configuration export"""
    print("Port Management System - Configuration Exporter")
    print("=" * 60)
    
    try:
        # Check if we can connect to the database
        with app.app_context():
            # Test database connection
            try:
                from sqlalchemy import text
                with db.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                print("Database connection: OK")
            except Exception as conn_error:
                print(f"Database connection failed: {conn_error}")
                raise
        
        print("\nChoose export format:")
        print("1. Console Report (detailed text)")
        print("2. JSON File (machine-readable)")
        print("3. Both")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice in ['1', '3']:
            print("\nGenerating configuration report...\n")
            format_configuration_report()
        
        if choice in ['2', '3']:
            print("\nExporting JSON configuration...")
            filename = export_json_config()
            print(f"JSON export saved as: {filename}")
        
        if choice not in ['1', '2', '3']:
            print("Invalid choice. Generating console report by default.")
            format_configuration_report()
        
        print("\nConfiguration export completed successfully!")
        
    except Exception as e:
        print(f"Error during configuration export: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the Flask app is properly configured")
        print("2. Check database connection settings")
        print("3. Ensure all required dependencies are installed")
        return 1
    
    return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)