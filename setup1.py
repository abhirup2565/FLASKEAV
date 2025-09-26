#!/usr/bin/env python3
"""
Port Management System Setup Script
Clears existing data (except admin) and creates comprehensive port management structure
"""

import os
import sys
from datetime import datetime, date, timedelta

# Add project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import *

def clear_database_except_admin():
    """Clear database while preserving admin user and admin role"""
    print("Clearing database (preserving admin user)...")
    
    with app.app_context():
        try:
            # Get admin user and role before clearing
            admin_user = User.query.filter_by(username='admin').first()
            admin_role = Role.query.filter_by(code='ADMIN').first()
            
            if not admin_user or not admin_role:
                print("Warning: Admin user or role not found!")
                return False
            
            print("Clearing entity data...")
            
            # Clear EAV data first
            AttributeValueText.query.delete()
            AttributeValueNumeric.query.delete()
            AttributeValueDatetime.query.delete()
            AttributeValueBoolean.query.delete()
            
            # Clear entity instances
            EntityInstance.query.delete()
            
            # Clear form configurations
            FormFieldConfiguration.query.delete()
            FormDefinition.query.delete()
            
            # Clear attribute definitions
            AttributeDefinition.query.delete()
            
            # Clear workflow and events
            WorkflowTransition.query.delete()
            WorkflowState.query.delete()
            EventConfiguration.query.delete()
            
            # Clear entity types
            EntityType.query.delete()
            
            # Clear other system data
            UserFavoriteModule.query.delete()
            EntityPermission.query.delete()
            UserOrganizationalAssignment.query.delete()
            OrganizationalUnit.query.delete()
            ApprovalType.query.delete()
            AuditLog.query.delete()
            SystemParameter.query.delete()
            
            # Clear user roles except admin
            UserRole.query.filter(
                ~((UserRole.user_id == admin_user.id) & (UserRole.role_id == admin_role.id))
            ).delete()
            
            # Clear users except admin
            User.query.filter(User.id != admin_user.id).delete()
            
            # Clear roles except admin
            Role.query.filter(Role.id != admin_role.id).delete()
            
            # Clear modules and applications
            Module.query.delete()
            Application.query.delete()
            
            db.session.commit()
            print("Database cleared successfully!")
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error clearing database: {e}")
            raise

def create_application_structure():
    """Create Port Management application and module"""
    print("Creating application structure...")
    
    # Create Port Management application
    application = Application(
        code='PORT_MGMT',
        name='Port Management System',
        description='Comprehensive port operations and vessel management system',
        icon='anchor',
        order_index=1,
        is_active=True,
        created_by='system'
    )
    db.session.add(application)
    db.session.flush()
    
    # Create Port Operations module
    module = Module(
        application_id=application.id,
        code='PORT_OPS',
        name='Port Operations',
        description='Port operations, vessel management, cargo handling and delay tracking',
        icon='directions_boat',
        order_index=1,
        is_system=False,
        is_active=True,
        created_by='system'
    )
    db.session.add(module)
    db.session.flush()
    
    print(f"Created: {application.name} > {module.name}")
    return application, module

def create_entity_with_forms(module_id, code, name, description, is_master, attributes_config):
    """Create entity type with attributes and default forms"""
    print(f"Creating {name}...")
    
    # Create entity type
    entity_type = EntityType(
        module_id=module_id,
        code=code,
        name=name,
        description=description,
        table_name=code.lower(),
        is_master=is_master,
        is_transactional=not is_master,
        icon='table_view' if is_master else 'receipt_long',
        order_index=len(attributes_config),
        is_active=True,
        created_by='system'
    )
    db.session.add(entity_type)
    db.session.flush()
    
    # Create attributes
    for i, (attr_code, attr_name, data_type, max_length, is_required, is_unique) in enumerate(attributes_config, 1):
        attr = AttributeDefinition(
            entity_type_id=entity_type.id,
            code=attr_code,
            name=attr_name,
            data_type=data_type,
            max_length=max_length,
            decimal_precision=12 if data_type == DataTypeEnum.DECIMAL else None,
            decimal_scale=2 if data_type == DataTypeEnum.DECIMAL else None,
            is_required=is_required,
            is_unique=is_unique,
            order_index=i,
            is_active=True,
            created_by='system'
        )
        db.session.add(attr)
    
    db.session.flush()
    
    # Create default forms
    create_default_forms(entity_type)
    
    print(f"Created {name} with {len(attributes_config)} attributes")
    return entity_type

def create_default_forms(entity_type):
    """Create default forms for an entity type"""
    forms_config = [
        (FormTypeEnum.LIST, 'List View', LayoutTypeEnum.SINGLE_COLUMN, 25),
        (FormTypeEnum.DETAIL, 'Detail View', LayoutTypeEnum.TWO_COLUMN, 1),
        (FormTypeEnum.CREATE, 'Create Form', LayoutTypeEnum.TWO_COLUMN, 1),
        (FormTypeEnum.EDIT, 'Edit Form', LayoutTypeEnum.TWO_COLUMN, 1)
    ]
    
    for form_type, form_name, layout, records_per_page in forms_config:
        # Create form definition
        form_def = FormDefinition(
            entity_type_id=entity_type.id,
            code=f"{entity_type.code}_{form_type.value}",
            name=f"{entity_type.name} {form_name}",
            form_type=form_type,
            layout_type=layout,
            records_per_page=records_per_page,
            is_default=True,
            is_active=True,
            created_by='system'
        )
        db.session.add(form_def)
        db.session.flush()
        
        # Get attributes for this entity
        attributes = AttributeDefinition.query.filter_by(
            entity_type_id=entity_type.id,
            is_active=True
        ).order_by(AttributeDefinition.order_index).all()
        
        # Create form field configurations
        for attr in attributes:
            field_type = get_field_type_for_attribute(attr)
            is_editable = form_type in [FormTypeEnum.CREATE, FormTypeEnum.EDIT]
            
            field_config = FormFieldConfiguration(
                form_definition_id=form_def.id,
                attribute_definition_id=attr.id,
                field_label=attr.name,
                field_type=field_type,
                order_index=attr.order_index,
                is_visible=True,
                is_editable=is_editable,
                is_required=attr.is_required and is_editable,
                is_searchable=(form_type == FormTypeEnum.LIST),
                is_sortable=(form_type == FormTypeEnum.LIST),
                created_by='system'
            )
            db.session.add(field_config)

def get_field_type_for_attribute(attr):
    """Determine field type based on attribute data type"""
    type_mapping = {
        DataTypeEnum.VARCHAR: FieldTypeEnum.TEXT,
        DataTypeEnum.TEXT: FieldTypeEnum.TEXTAREA,
        DataTypeEnum.INT: FieldTypeEnum.NUMBER,
        DataTypeEnum.BIGINT: FieldTypeEnum.NUMBER,
        DataTypeEnum.DECIMAL: FieldTypeEnum.DECIMAL,
        DataTypeEnum.BOOLEAN: FieldTypeEnum.CHECKBOX,
        DataTypeEnum.DATE: FieldTypeEnum.DATE,
        DataTypeEnum.DATETIME: FieldTypeEnum.DATETIME
    }
    return type_mapping.get(attr.data_type, FieldTypeEnum.TEXT)

def setup_dropdown_connections():
    """Configure dropdown connections between entities"""
    print("Setting up dropdown connections...")
    
    # Helper function to find entities and attributes
    def get_entity_and_attr(entity_code, attr_code):
        entity = EntityType.query.filter_by(code=entity_code).first()
        if not entity:
            return None, None
        attr = AttributeDefinition.query.filter_by(entity_type_id=entity.id, code=attr_code).first()
        return entity, attr
    
    # Dropdown connections configuration
    connections = [
        # Vessel Tally dropdowns
        ('VESSEL_TALLY', 'OPERATION_TYPE', 'OPERATION_TYPE_MASTER', 'OPERATION_TYPE_NAME', 'OPERATION_TYPE_NAME'),
        ('VESSEL_TALLY', 'VESSEL_NAME', 'VESSEL_PROFILE', 'VESSEL_NAME', 'VESSEL_NAME'),
        ('VESSEL_TALLY', 'VESSEL_OPERATION_COMPLETED_FLAG', 'STATUS_MASTER', 'STATUS_NAME', 'STATUS_NAME'),
        
        # Operation Recording dropdowns
        ('OPERATION_RECORDING', 'VESSEL_TALLY_DOC_NO', 'VESSEL_TALLY', 'DOC_NO', 'DOC_NO'),
        ('OPERATION_RECORDING', 'HATCH_NAME', 'EQUIPMENT_MASTER', 'EQUIPMENT_NAME', 'EQUIPMENT_NAME'),
        ('OPERATION_RECORDING', 'CARGO_NAME', 'CARGO_MASTER', 'CARGO_NAME', 'CARGO_NAME'),
        ('OPERATION_RECORDING', 'UOM_NAME', 'UOM_MASTER', 'UOM_NAME', 'UOM_NAME'),
        
        # Delay Transaction dropdowns
        ('DELAY_TRANSACTION', 'VESSEL_TALLY_DOC_NO', 'VESSEL_TALLY', 'DOC_NO', 'DOC_NO'),
        ('DELAY_TRANSACTION', 'HATCH_NAME', 'EQUIPMENT_MASTER', 'EQUIPMENT_NAME', 'EQUIPMENT_NAME'),
        ('DELAY_TRANSACTION', 'TANK_NAME', 'EQUIPMENT_MASTER', 'EQUIPMENT_NAME', 'EQUIPMENT_NAME'),
        ('DELAY_TRANSACTION', 'DELAY_NAME', 'DELAY_MASTER', 'DELAY_NAME', 'DELAY_NAME'),
    ]
    
    for target_entity_code, target_attr_code, source_entity_code, source_attr_code, display_attr_code in connections:
        # Get entities and attributes
        target_entity, target_attr = get_entity_and_attr(target_entity_code, target_attr_code)
        source_entity, source_attr = get_entity_and_attr(source_entity_code, source_attr_code)
        
        if not all([target_entity, target_attr, source_entity, source_attr]):
            print(f"Skipping connection: {target_entity_code}.{target_attr_code} -> {source_entity_code}.{source_attr_code}")
            continue
        
        display_attr = source_attr  # Use source attribute for display by default
        if display_attr_code != source_attr_code:
            display_attr = AttributeDefinition.query.filter_by(entity_type_id=source_entity.id, code=display_attr_code).first()
        
        # Find form field configurations for CREATE forms and update them
        create_form = FormDefinition.query.filter_by(
            entity_type_id=target_entity.id,
            form_type=FormTypeEnum.CREATE,
            is_active=True
        ).first()
        
        if create_form:
            field_config = FormFieldConfiguration.query.filter_by(
                form_definition_id=create_form.id,
                attribute_definition_id=target_attr.id
            ).first()
            
            if field_config:
                field_config.field_type = FieldTypeEnum.SELECT
                field_config.dropdown_source_entity_id = source_entity.id
                field_config.dropdown_source_attribute_id = source_attr.id
                field_config.dropdown_display_attribute_id = display_attr.id if display_attr else source_attr.id
                field_config.show_unique_values_only = True
                print(f"Connected: {target_entity_code}.{target_attr_code} -> {source_entity_code}.{source_attr_code}")

def create_sample_data():
    """Create sample data for testing"""
    print("Creating sample data...")
    
    # Sample data for master entities
    sample_data = {
        'OPERATION_TYPE_MASTER': [
            {'OPERATION_TYPE_NAME': 'Discharge'},
            {'OPERATION_TYPE_NAME': 'Load'}
        ],
        'STATUS_MASTER': [
            {'STATUS_NAME': 'YES'},
            {'STATUS_NAME': 'NO'}
        ],
        'CARGO_MASTER': [
            {'CARGO_NAME': 'Container Cargo', 'NATURE_OF_CARGO': 'Containerized', 'CATEGORY': 'General'},
            {'CARGO_NAME': 'Coal', 'NATURE_OF_CARGO': 'Dry Bulk', 'CATEGORY': 'Bulk'},
            {'CARGO_NAME': 'Iron Ore', 'NATURE_OF_CARGO': 'Dry Bulk', 'CATEGORY': 'Bulk'},
            {'CARGO_NAME': 'Crude Oil', 'NATURE_OF_CARGO': 'Liquid Bulk', 'CATEGORY': 'Liquid'}
        ],
        'UOM_MASTER': [
            {'UOM_NAME': 'Metric Tons'},
            {'UOM_NAME': 'TEU'},
            {'UOM_NAME': 'CBM'},
            {'UOM_NAME': 'Liters'}
        ],
        'EQUIPMENT_MASTER': [
            {'EQUIPMENT_NAME': 'Hatch 1', 'EQUIPMENT_TYPE': 'HATCH'},
            {'EQUIPMENT_NAME': 'Hatch 2', 'EQUIPMENT_TYPE': 'HATCH'},
            {'EQUIPMENT_NAME': 'Hatch 3', 'EQUIPMENT_TYPE': 'HATCH'},
            {'EQUIPMENT_NAME': 'Tank 1', 'EQUIPMENT_TYPE': 'TANK'},
            {'EQUIPMENT_NAME': 'Tank 2', 'EQUIPMENT_TYPE': 'TANK'}
        ],
        'DELAY_MASTER': [
            {'DELAY_NAME': 'Weather Delay', 'DELAY_CATEGORY': 'Natural'},
            {'DELAY_NAME': 'Equipment Breakdown', 'DELAY_CATEGORY': 'Technical'},
            {'DELAY_NAME': 'Documentation Delay', 'DELAY_CATEGORY': 'Administrative'},
            {'DELAY_NAME': 'Cargo Hold Up', 'DELAY_CATEGORY': 'Operational'}
        ],
        'VESSEL_PROFILE': [
            {
                'DOC_NO': 'VP001',
                'STATUS': 'Active',
                'VESSEL_TYPE': 'Container',
                'VESSEL_NAME': 'MSC Harmony',
                'IMO_OFFICIAL_NO': '9876543',
                'CALL_SIGN': 'ABCD1',
                'NATIONALITY': 'Panama',
                'LOA_METERS': 350.0,
                'BEAM_METERS': 45.0,
                'GRT_MT': 150000.0,
                'DWT_MT': 180000.0
            }
        ]
    }
    
    # Create sample instances for each entity
    for entity_code, records in sample_data.items():
        entity_type = EntityType.query.filter_by(code=entity_code).first()
        if not entity_type:
            continue
            
        for record_data in records:
            try:
                instance = create_entity_instance_with_attributes(
                    entity_type_id=entity_type.id,
                    attribute_values=record_data,
                    created_by='system'
                )
                print(f"Created sample data for {entity_code}")
            except Exception as e:
                print(f"Error creating sample data for {entity_code}: {e}")

def main():
    """Main setup function"""
    print("=" * 80)
    print("PORT MANAGEMENT SYSTEM - COMPREHENSIVE SETUP")
    print("=" * 80)
    
    with app.app_context():
        try:
            # Step 1: Clear existing data
            if not clear_database_except_admin():
                return
            
            # Step 2: Create application structure
            application, module = create_application_structure()
            
            # Step 3: Create master entities
            print("\nCreating Master Entities...")
            
            # Vessel Profile (Master)
            create_entity_with_forms(module.id, 'VESSEL_PROFILE', 'Vessel Profile', 'Master vessel information and documentation', True, [
                ('DOC_NO', 'Doc No', DataTypeEnum.VARCHAR, 50, True, True),
                ('STATUS', 'Status', DataTypeEnum.VARCHAR, 20, True, False),
                ('VESSEL_TYPE', 'Vessel Type', DataTypeEnum.VARCHAR, 50, False, False),
                ('VESSEL_TYPE_NAME', 'Vessel Type Name', DataTypeEnum.VARCHAR, 100, False, False),
                ('VESSEL_NAME', 'Vessel Name', DataTypeEnum.VARCHAR, 100, True, False),
                ('IMO_OFFICIAL_NO', 'IMO Official No', DataTypeEnum.VARCHAR, 20, True, True),
                ('CALL_SIGN', 'Call Sign', DataTypeEnum.VARCHAR, 20, False, False),
                ('VESSEL_DELIVERY_DATE', 'Vessel Delivery Date', DataTypeEnum.DATETIME, None, False, False),
                ('PORT_OF_REGISTRATION', 'Port of Registration', DataTypeEnum.VARCHAR, 100, False, False),
                ('NATIONALITY', 'Nationality', DataTypeEnum.VARCHAR, 50, False, False),
                ('AGENCY_TYPE', 'Agency Type', DataTypeEnum.VARCHAR, 50, False, False),
                ('CLASS_CERTIFICATE_CATEGORY', 'Class Certificate Category', DataTypeEnum.VARCHAR, 50, False, False),
                ('AGENCY_NAME', 'Agency Name', DataTypeEnum.VARCHAR, 100, False, False),
                ('PORT_OF_SUBMISSION', 'Port of Submission', DataTypeEnum.VARCHAR, 100, False, False),
                ('SHIP_REGISTRY_CERT_NO', 'Ship Registry Certificate No', DataTypeEnum.VARCHAR, 50, False, False),
                ('LOA_METERS', 'LOA Meters', DataTypeEnum.DECIMAL, None, False, False),
                ('BEAM_METERS', 'Beam Meters', DataTypeEnum.DECIMAL, None, False, False),
                ('GRT_MT', 'GRT MT', DataTypeEnum.DECIMAL, None, False, False),
                ('DWT_MT', 'DWT MT', DataTypeEnum.DECIMAL, None, False, False),
                ('VESSEL_OWNER_NAME', 'Vessel Owner Name', DataTypeEnum.VARCHAR, 100, False, False),
                ('VESSEL_PROFILE_VALIDITY', 'Vessel Profile Validity', DataTypeEnum.DATE, None, False, False),
                ('INTEGRATION_PCS_REF_NO', 'Integration PCS Ref Number', DataTypeEnum.VARCHAR, 50, False, False),
                ('DOC_APPROVED_DATE', 'Doc Approved Date', DataTypeEnum.DATE, None, False, False),
                ('DATA_SOURCE', 'Data Source', DataTypeEnum.VARCHAR, 50, False, False),
                ('DOC_DATE', 'Doc Date', DataTypeEnum.DATE, None, False, False)
            ])
            
            # Operation Type Master
            create_entity_with_forms(module.id, 'OPERATION_TYPE_MASTER', 'Operation Type Master', 'Types of operations (Discharge/Load)', True, [
                ('OPERATION_TYPE_NAME', 'Operation Type Name', DataTypeEnum.VARCHAR, 50, True, True),
                ('DESCRIPTION', 'Description', DataTypeEnum.TEXT, None, False, False)
            ])
            
            # Status Master
            create_entity_with_forms(module.id, 'STATUS_MASTER', 'Status Master', 'Status values (YES/NO)', True, [
                ('STATUS_NAME', 'Status Name', DataTypeEnum.VARCHAR, 50, True, True),
                ('DESCRIPTION', 'Description', DataTypeEnum.TEXT, None, False, False)
            ])
            
            # Cargo Master
            create_entity_with_forms(module.id, 'CARGO_MASTER', 'Cargo Master', 'Types of cargo handled', True, [
                ('CARGO_NAME', 'Cargo Name', DataTypeEnum.VARCHAR, 100, True, True),
                ('NATURE_OF_CARGO', 'Nature of Cargo', DataTypeEnum.VARCHAR, 100, False, False),
                ('CATEGORY', 'Category', DataTypeEnum.VARCHAR, 50, False, False),
                ('DESCRIPTION', 'Description', DataTypeEnum.TEXT, None, False, False)
            ])
            
            # UOM Master
            create_entity_with_forms(module.id, 'UOM_MASTER', 'UOM Master', 'Units of measurement', True, [
                ('UOM_NAME', 'UOM Name', DataTypeEnum.VARCHAR, 50, True, True),
                ('DESCRIPTION', 'Description', DataTypeEnum.TEXT, None, False, False)
            ])
            
            # Equipment Master
            create_entity_with_forms(module.id, 'EQUIPMENT_MASTER', 'Equipment Master', 'Port equipment (Hatches, Tanks)', True, [
                ('EQUIPMENT_NAME', 'Equipment Name', DataTypeEnum.VARCHAR, 100, True, True),
                ('EQUIPMENT_TYPE', 'Equipment Type', DataTypeEnum.VARCHAR, 50, False, False),
                ('DESCRIPTION', 'Description', DataTypeEnum.TEXT, None, False, False)
            ])
            
            # Delay Master
            create_entity_with_forms(module.id, 'DELAY_MASTER', 'Delay Master', 'Types of delays and stoppages', True, [
                ('DELAY_NAME', 'Delay Name', DataTypeEnum.VARCHAR, 100, True, True),
                ('DELAY_CATEGORY', 'Delay Category', DataTypeEnum.VARCHAR, 50, False, False),
                ('DESCRIPTION', 'Description', DataTypeEnum.TEXT, None, False, False)
            ])
            
            # Step 4: Create transactional entities
            print("\nCreating Transactional Entities...")
            
            # Vessel Tally
            create_entity_with_forms(module.id, 'VESSEL_TALLY', 'Vessel Tally', 'Vessel arrival and operation details', False, [
                ('DOC_NO', 'Doc No', DataTypeEnum.VARCHAR, 50, True, True),
                ('STATUS', 'Status', DataTypeEnum.VARCHAR, 20, False, False),
                ('OPERATION_TYPE', 'Operation Type', DataTypeEnum.VARCHAR, 20, True, False),
                ('VCN_NO', 'VCN No', DataTypeEnum.VARCHAR, 50, True, False),
                ('VESSEL_NAME', 'Vessel Name', DataTypeEnum.VARCHAR, 100, True, False),
                ('IMO_NUMBER', 'IMO Number', DataTypeEnum.VARCHAR, 20, True, False),
                ('IGM_NO', 'IGM No', DataTypeEnum.VARCHAR, 50, False, False),
                ('FIRST_LINE_ASHORE_DATE', 'First Line Ashore Date', DataTypeEnum.DATE, None, False, False),
                ('LAST_LINE_ASHORE_DATE', 'Last Line Ashore Date', DataTypeEnum.DATE, None, False, False),
                ('GANGWAY_DOWN_DATE', 'Gangway Down Date', DataTypeEnum.DATE, None, False, False),
                ('VESSEL_OPERATION_COMPLETED_FLAG', 'Vessel Operation Completed Flag', DataTypeEnum.VARCHAR, 10, False, False)
            ])
            
            # Operation Recording
            create_entity_with_forms(module.id, 'OPERATION_RECORDING', 'Operation Recording', 'Cargo operation details', False, [
                ('VESSEL_TALLY_DOC_NO', 'Vessel Tally Doc No', DataTypeEnum.VARCHAR, 50, True, False),
                ('HATCH_NAME', 'Hatch Name', DataTypeEnum.VARCHAR, 100, False, False),
                ('NATURE_OF_CARGO', 'Nature of Cargo', DataTypeEnum.VARCHAR, 100, False, False),
                ('CARGO_NAME', 'Cargo Name', DataTypeEnum.VARCHAR, 100, False, False),
                ('UOM_NAME', 'UOM Name', DataTypeEnum.VARCHAR, 50, False, False),
                ('DISCHARGED_LOADED_TONNAGE', 'Discharged Loaded Tonnage', DataTypeEnum.DECIMAL, None, False, False),
                ('START_DATE', 'Start Date', DataTypeEnum.DATETIME, None, True, False),
                ('END_DATE', 'End Date', DataTypeEnum.DATETIME, None, True, False)
            ])
            
            # Delay Transaction
            create_entity_with_forms(module.id, 'DELAY_TRANSACTION', 'Delay Transaction', 'Delay and stoppage tracking', False, [
                ('VESSEL_TALLY_DOC_NO', 'Vessel Tally Doc No', DataTypeEnum.VARCHAR, 50, True, False),
                ('HATCH_NAME', 'Hatch Name', DataTypeEnum.VARCHAR, 100, False, False),
                ('TANK_NAME', 'Tank Name', DataTypeEnum.VARCHAR, 100, False, False),
                ('START_DATE', 'Start Date', DataTypeEnum.DATETIME, None, True, False),
                ('END_DATE', 'End Date', DataTypeEnum.DATETIME, None, True, False),
                ('DELAY_NAME', 'Delay Name', DataTypeEnum.VARCHAR, 100, True, False),
                ('STOPPAGE_REMARKS', 'Stoppage Remarks', DataTypeEnum.TEXT, None, False, False)
            ])
            
            # Step 5: Setup dropdown connections
            setup_dropdown_connections()
            
            # Step 6: Create sample data
            create_sample_data()
            
            # Final commit
            db.session.commit()
            
            print("\n" + "=" * 80)
            print("PORT MANAGEMENT SETUP COMPLETED!")
            print("=" * 80)
            print(f"Application: Port Management System")
            print(f"Module: Port Operations")
            print(f"Master Entities: 7 (Vessel Profile, Operation Type, Status, Cargo, UOM, Equipment, Delay)")
            print(f"Transactional Entities: 3 (Vessel Tally, Operation Recording, Delay Transaction)")
            print(f"Dropdown Connections: 12 configured")
            print("")
            print("Access at: http://localhost:5000/")
            print("Admin at: http://localhost:5000/custom-admin/")
            print("Entity Designer at: http://localhost:5000/entity-designer/")
            print("Login: admin / admin123")
            print("=" * 80)
            
        except Exception as e:
            db.session.rollback()
            print(f"Setup failed: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    print("Port Management System - Comprehensive Setup")
    print("This will CLEAR ALL DATA except admin user!")
    print("")
    
    response = input("Continue? (y/N): ").strip().lower()
    if response != 'y':
        print("Setup cancelled.")
        sys.exit(0)
    
    try:
        main()
        print("\nSetup completed successfully!")
    except Exception as e:
        print(f"\nSetup failed: {e}")
        sys.exit(1)