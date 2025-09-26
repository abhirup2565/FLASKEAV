# entity_designer/__init__.py
"""
Entity Designer - Unified Entity Management Interface
Single-page admin for managing entities, attributes, and forms
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import and_, or_
from models import *
import json
from datetime import datetime

# Create blueprint
entity_designer_bp = Blueprint('entity_designer', __name__, 
                              url_prefix='/entity-designer', 
                              template_folder='templates')

class EntityDesignerConfig:
    """Configuration for the Entity Designer interface"""
    
    FIELD_TYPE_OPTIONS = [
        ('TEXT', 'Text Input'),
        ('TEXTAREA', 'Text Area'),
        ('NUMBER', 'Number'),
        ('DECIMAL', 'Decimal'),
        ('EMAIL', 'Email'),
        ('PASSWORD', 'Password'),
        ('CHECKBOX', 'Checkbox'),
        ('SELECT', 'Dropdown Select'),
        ('MULTISELECT', 'Multi-Select'),
        ('DATE', 'Date'),
        ('DATETIME', 'Date & Time'),
        ('FILE', 'File Upload'),
        ('IMAGE', 'Image Upload')
    ]
    
    DATA_TYPE_OPTIONS = [
        ('VARCHAR', 'Text (VARCHAR)'),
        ('TEXT', 'Long Text'),
        ('INT', 'Integer'),
        ('BIGINT', 'Big Integer'),
        ('DECIMAL', 'Decimal'),
        ('BOOLEAN', 'Boolean'),
        ('DATE', 'Date'),
        ('DATETIME', 'Date Time'),
        ('JSON', 'JSON Data')
    ]
    
    FORM_TYPE_OPTIONS = [
        ('LIST', 'List View'),
        ('DETAIL', 'Detail View'),
        ('CREATE', 'Create Form'),
        ('EDIT', 'Edit Form'),
        ('SEARCH', 'Search Form')
    ]

class EntityDesignerUtils:
    """Utility functions for Entity Designer"""
    
    @staticmethod
    def get_entity_summary(entity_type):
        """Get comprehensive summary of entity configuration"""
        attributes_count = entity_type.attribute_definitions.filter_by(is_active=True).count()
        forms_count = entity_type.form_definitions.filter_by(is_active=True).count()
        instances_count = entity_type.entity_instances.filter_by(is_active=True).count()
        
        return {
            'id': entity_type.id,
            'code': entity_type.code,
            'name': entity_type.name,
            'description': entity_type.description,
            'module': entity_type.module.name,
            'application': entity_type.module.application.name,
            'is_master': entity_type.is_master,
            'is_transactional': entity_type.is_transactional,
            'attributes_count': attributes_count,
            'forms_count': forms_count,
            'instances_count': instances_count,
            'icon': entity_type.icon or 'table_view'
        }
    
    @staticmethod
    def get_entity_details(entity_type_id):
        """Get complete entity configuration including attributes and forms"""
        entity_type = EntityType.query.get(entity_type_id)
        if not entity_type:
            return None
        
        # Get attributes with their form configurations
        attributes = []
        attr_definitions = AttributeDefinition.query.filter_by(
            entity_type_id=entity_type_id,
            is_active=True
        ).order_by(AttributeDefinition.order_index).all()
        
        for attr in attr_definitions:
            attr_data = {
                'id': attr.id,
                'code': attr.code,
                'name': attr.name,
                'description': attr.description,
                'data_type': attr.data_type.value,
                'max_length': attr.max_length,
                'is_required': attr.is_required,
                'is_unique': attr.is_unique,
                'default_value': attr.default_value,
                'order_index': attr.order_index,
                'form_configs': []
            }
            
            # Get form field configurations for this attribute
            form_configs = FormFieldConfiguration.query.filter_by(
                attribute_definition_id=attr.id
            ).join(FormDefinition).all()
            
            for config in form_configs:
                config_data = {
                    'id': config.id,
                    'form_type': config.form_definition.form_type.value,
                    'field_type': config.field_type.value,
                    'field_label': config.field_label,
                    'is_visible': config.is_visible,
                    'is_editable': config.is_editable,
                    'is_required': config.is_required,
                    'order_index': config.order_index,
                    'dropdown_source_entity_id': config.dropdown_source_entity_id,
                    'dropdown_source_attribute_id': config.dropdown_source_attribute_id,
                    'show_unique_values_only': config.show_unique_values_only
                }
                attr_data['form_configs'].append(config_data)
            
            attributes.append(attr_data)
        
        # Get forms summary
        forms = []
        form_definitions = FormDefinition.query.filter_by(
            entity_type_id=entity_type_id,
            is_active=True
        ).all()
        
        for form in form_definitions:
            form_data = {
                'id': form.id,
                'code': form.code,
                'name': form.name,
                'form_type': form.form_type.value,
                'layout_type': form.layout_type.value,
                'is_default': form.is_default,
                'field_count': form.form_field_configurations.filter_by(is_visible=True).count()
            }
            forms.append(form_data)
        
        return {
            'entity': EntityDesignerUtils.get_entity_summary(entity_type),
            'attributes': attributes,
            'forms': forms
        }
    
    @staticmethod
    def create_default_forms(entity_type_id):
        """Create default forms for an entity type"""
        entity_type = EntityType.query.get(entity_type_id)
        if not entity_type:
            return False
        
        # Get all attributes
        attributes = AttributeDefinition.query.filter_by(
            entity_type_id=entity_type_id,
            is_active=True
        ).order_by(AttributeDefinition.order_index).all()
        
        form_types = [
            (FormTypeEnum.LIST, 'List View', LayoutTypeEnum.SINGLE_COLUMN),
            (FormTypeEnum.DETAIL, 'Detail View', LayoutTypeEnum.TWO_COLUMN),
            (FormTypeEnum.CREATE, 'Create Form', LayoutTypeEnum.TWO_COLUMN),
            (FormTypeEnum.EDIT, 'Edit Form', LayoutTypeEnum.TWO_COLUMN)
        ]
        
        try:
            for form_type, form_name, layout_type in form_types:
                # Create form definition
                form_def = FormDefinition(
                    entity_type_id=entity_type_id,
                    code=f"{entity_type.code}_{form_type.value}",
                    name=f"{entity_type.name} {form_name}",
                    form_type=form_type,
                    layout_type=layout_type,
                    records_per_page=25 if form_type == FormTypeEnum.LIST else 1,
                    is_default=True,
                    is_active=True,
                    created_by=current_user.username
                )
                db.session.add(form_def)
                db.session.flush()
                
                # Create field configurations for each attribute
                for attr in attributes:
                    field_type = EntityDesignerUtils.get_default_field_type(attr)
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
                        created_by=current_user.username
                    )
                    db.session.add(field_config)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating default forms: {e}")
            return False
    
    @staticmethod
    def get_default_field_type(attribute):
        """Determine default field type for an attribute"""
        mapping = {
            DataTypeEnum.VARCHAR: FieldTypeEnum.TEXT,
            DataTypeEnum.TEXT: FieldTypeEnum.TEXTAREA,
            DataTypeEnum.INT: FieldTypeEnum.NUMBER,
            DataTypeEnum.BIGINT: FieldTypeEnum.NUMBER,
            DataTypeEnum.DECIMAL: FieldTypeEnum.DECIMAL,
            DataTypeEnum.BOOLEAN: FieldTypeEnum.CHECKBOX,
            DataTypeEnum.DATE: FieldTypeEnum.DATE,
            DataTypeEnum.DATETIME: FieldTypeEnum.DATETIME
        }
        return mapping.get(attribute.data_type, FieldTypeEnum.TEXT)

# Main Entity Designer Routes

@entity_designer_bp.route('/')
@login_required
def index():
    """Main Entity Designer interface"""
    # Get all modules with their entities
    modules = Module.query.filter_by(is_active=True).join(Application).order_by(
        Application.order_index, 
        Module.order_index
    ).all()
    
    entity_summaries = []
    for module in modules:
        entity_types = module.entity_types.filter_by(is_active=True).order_by(EntityType.order_index).all()
        for entity_type in entity_types:
            summary = EntityDesignerUtils.get_entity_summary(entity_type)
            entity_summaries.append(summary)
    
    return render_template('entity_designer/index.html', 
                         entity_summaries=entity_summaries,
                         modules=modules)

@entity_designer_bp.route('/entity/<int:entity_id>')
@login_required
def entity_detail(entity_id):
    """Get entity details via AJAX"""
    details = EntityDesignerUtils.get_entity_details(entity_id)
    if not details:
        return jsonify({'error': 'Entity not found'}), 404
    
    return jsonify(details)

@entity_designer_bp.route('/entity/<int:entity_id>/save', methods=['POST'])
@login_required
def save_entity(entity_id):
    """Save entity configuration"""
    try:
        data = request.json
        entity_type = EntityType.query.get(entity_id)
        if not entity_type:
            return jsonify({'error': 'Entity not found'}), 404
        
        # Update entity basic info
        if 'entity' in data:
            entity_info = data['entity']
            entity_type.name = entity_info.get('name', entity_type.name)
            entity_type.description = entity_info.get('description', entity_type.description)
            entity_type.icon = entity_info.get('icon', entity_type.icon)
            entity_type.is_master = entity_info.get('is_master', entity_type.is_master)
            entity_type.is_transactional = entity_info.get('is_transactional', entity_type.is_transactional)
            entity_type.updated_by = current_user.username
        
        # Update attributes
        if 'attributes' in data:
            for attr_data in data['attributes']:
                attr_id = attr_data.get('id')
                if attr_id:
                    # Update existing attribute
                    attr = AttributeDefinition.query.get(attr_id)
                    if attr and attr.entity_type_id == entity_id:
                        attr.name = attr_data.get('name', attr.name)
                        attr.description = attr_data.get('description', attr.description)
                        attr.is_required = attr_data.get('is_required', attr.is_required)
                        attr.is_unique = attr_data.get('is_unique', attr.is_unique)
                        attr.max_length = attr_data.get('max_length', attr.max_length)
                        attr.default_value = attr_data.get('default_value', attr.default_value)
                        attr.order_index = attr_data.get('order_index', attr.order_index)
                        attr.updated_by = current_user.username
                else:
                    # Create new attribute
                    data_type = DataTypeEnum(attr_data.get('data_type', 'VARCHAR'))
                    new_attr = AttributeDefinition(
                        entity_type_id=entity_id,
                        code=attr_data.get('code', ''),
                        name=attr_data.get('name', ''),
                        description=attr_data.get('description', ''),
                        data_type=data_type,
                        max_length=attr_data.get('max_length'),
                        is_required=attr_data.get('is_required', False),
                        is_unique=attr_data.get('is_unique', False),
                        default_value=attr_data.get('default_value'),
                        order_index=attr_data.get('order_index', 0),
                        is_active=True,
                        created_by=current_user.username
                    )
                    db.session.add(new_attr)
        
        # Update form field configurations
        if 'form_configs' in data:
            for config_data in data['form_configs']:
                config_id = config_data.get('id')
                if config_id:
                    config = FormFieldConfiguration.query.get(config_id)
                    if config:
                        config.field_type = FieldTypeEnum(config_data.get('field_type', config.field_type.value))
                        config.field_label = config_data.get('field_label', config.field_label)
                        config.is_visible = config_data.get('is_visible', config.is_visible)
                        config.is_editable = config_data.get('is_editable', config.is_editable)
                        config.is_required = config_data.get('is_required', config.is_required)
                        config.order_index = config_data.get('order_index', config.order_index)
                        
                        # Handle dropdown configuration
                        if config_data.get('dropdown_source_entity_id'):
                            config.dropdown_source_entity_id = config_data['dropdown_source_entity_id']
                            config.dropdown_source_attribute_id = config_data.get('dropdown_source_attribute_id')
                            config.show_unique_values_only = config_data.get('show_unique_values_only', False)
                        
                        config.updated_by = current_user.username
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Entity saved successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@entity_designer_bp.route('/entity/<int:entity_id>/attribute', methods=['POST'])
@login_required
def add_attribute(entity_id):
    """Add new attribute to entity"""
    try:
        data = request.json
        entity_type = EntityType.query.get(entity_id)
        if not entity_type:
            return jsonify({'error': 'Entity not found'}), 404
        
        # Get next order index
        max_order = db.session.query(db.func.max(AttributeDefinition.order_index)).filter_by(
            entity_type_id=entity_id
        ).scalar() or 0
        
        # Create new attribute
        attribute = AttributeDefinition(
            entity_type_id=entity_id,
            code=data.get('code', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            data_type=DataTypeEnum(data.get('data_type', 'VARCHAR')),
            max_length=data.get('max_length'),
            is_required=data.get('is_required', False),
            is_unique=data.get('is_unique', False),
            order_index=max_order + 1,
            is_active=True,
            created_by=current_user.username
        )
        db.session.add(attribute)
        db.session.flush()
        
        # Auto-create form field configurations for existing forms
        existing_forms = FormDefinition.query.filter_by(
            entity_type_id=entity_id,
            is_active=True
        ).all()
        
        for form_def in existing_forms:
            field_type = EntityDesignerUtils.get_default_field_type(attribute)
            is_editable = form_def.form_type in [FormTypeEnum.CREATE, FormTypeEnum.EDIT]
            
            field_config = FormFieldConfiguration(
                form_definition_id=form_def.id,
                attribute_definition_id=attribute.id,
                field_label=attribute.name,
                field_type=field_type,
                order_index=attribute.order_index,
                is_visible=True,
                is_editable=is_editable,
                is_required=attribute.is_required and is_editable,
                created_by=current_user.username
            )
            db.session.add(field_config)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'attribute_id': attribute.id,
            'message': 'Attribute added successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@entity_designer_bp.route('/entity/<int:entity_id>/attribute/<int:attr_id>', methods=['DELETE'])
@login_required
def delete_attribute(entity_id, attr_id):
    """Delete attribute and its form configurations"""
    try:
        attribute = AttributeDefinition.query.filter_by(
            id=attr_id,
            entity_type_id=entity_id
        ).first()
        
        if not attribute:
            return jsonify({'error': 'Attribute not found'}), 404
        
        # Check if attribute is used in any instances
        instance_count = 0
        if attribute.data_type in [DataTypeEnum.VARCHAR, DataTypeEnum.TEXT]:
            instance_count = AttributeValueText.query.filter_by(
                attribute_definition_id=attr_id
            ).count()
        elif attribute.data_type in [DataTypeEnum.INT, DataTypeEnum.BIGINT, DataTypeEnum.DECIMAL]:
            instance_count = AttributeValueNumeric.query.filter_by(
                attribute_definition_id=attr_id
            ).count()
        # Add other type checks as needed
        
        if instance_count > 0:
            return jsonify({
                'error': f'Cannot delete attribute. It has {instance_count} data records.'
            }), 400
        
        # Delete form field configurations first
        FormFieldConfiguration.query.filter_by(
            attribute_definition_id=attr_id
        ).delete()
        
        # Delete attribute
        db.session.delete(attribute)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Attribute deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@entity_designer_bp.route('/entity/<int:entity_id>/generate-forms', methods=['POST'])
@login_required
def generate_default_forms(entity_id):
    """Generate default forms for entity"""
    try:
        success = EntityDesignerUtils.create_default_forms(entity_id)
        if success:
            return jsonify({'success': True, 'message': 'Default forms generated successfully'})
        else:
            return jsonify({'error': 'Failed to generate forms'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@entity_designer_bp.route('/dropdown-sources')
@login_required
def get_dropdown_sources():
    """Get available entities and attributes for dropdown configuration"""
    entities = EntityType.query.filter_by(is_active=True).all()
    
    entity_data = []
    for entity in entities:
        attributes = AttributeDefinition.query.filter_by(
            entity_type_id=entity.id,
            is_active=True
        ).order_by(AttributeDefinition.order_index).all()
        
        entity_data.append({
            'id': entity.id,
            'name': entity.name,
            'code': entity.code,
            'attributes': [{
                'id': attr.id,
                'code': attr.code,
                'name': attr.name,
                'data_type': attr.data_type.value
            } for attr in attributes]
        })
    
    return jsonify(entity_data)

@entity_designer_bp.route('/entity/<int:entity_id>/form-config', methods=['POST'])
@login_required
def save_form_config(entity_id):
    """Save form field configuration"""
    try:
        data = request.json
        entity_type = EntityType.query.get(entity_id)
        if not entity_type:
            return jsonify({'error': 'Entity not found'}), 404
        
        form_type = FormTypeEnum(data.get('form_type'))
        attribute_id = data.get('attribute_id')
        
        # Find or create form definition
        form_def = FormDefinition.query.filter_by(
            entity_type_id=entity_id,
            form_type=form_type,
            is_active=True
        ).first()
        
        if not form_def:
            return jsonify({'error': 'Form definition not found'}), 404
        
        # Find or create form field configuration
        field_config = FormFieldConfiguration.query.filter_by(
            form_definition_id=form_def.id,
            attribute_definition_id=attribute_id
        ).first()
        
        if not field_config:
            field_config = FormFieldConfiguration(
                form_definition_id=form_def.id,
                attribute_definition_id=attribute_id,
                field_label=data.get('field_label', ''),
                field_type=FieldTypeEnum(data.get('field_type', 'TEXT')),
                order_index=data.get('order_index', 0),
                is_visible=True,
                is_editable=True,
                is_required=False,
                created_by=current_user.username
            )
            db.session.add(field_config)
        
        # Update configuration
        if 'field_type' in data:
            field_config.field_type = FieldTypeEnum(data['field_type'])
        if 'is_visible' in data:
            field_config.is_visible = data['is_visible']
        if 'is_editable' in data:
            field_config.is_editable = data['is_editable']
        if 'is_required' in data:
            field_config.is_required = data['is_required']
        if 'dropdown_source_entity_id' in data:
            field_config.dropdown_source_entity_id = data['dropdown_source_entity_id'] or None
        if 'dropdown_source_attribute_id' in data:
            field_config.dropdown_source_attribute_id = data['dropdown_source_attribute_id'] or None
        if 'show_unique_values_only' in data:
            field_config.show_unique_values_only = data['show_unique_values_only']
        
        field_config.updated_by = current_user.username
        field_config.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Form configuration saved successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@entity_designer_bp.route('/create-entity', methods=['POST'])
@login_required
def create_entity():
    """Create new entity type"""
    try:
        data = request.json
        
        # Get module
        module = Module.query.get(data.get('module_id'))
        if not module:
            return jsonify({'error': 'Module not found'}), 404
        
        # Create entity type
        entity_type = EntityType(
            module_id=data['module_id'],
            code=data['code'],
            name=data['name'],
            description=data.get('description', ''),
            icon=data.get('icon', 'table_view'),
            is_master=data.get('is_master', False),
            is_transactional=data.get('is_transactional', True),
            order_index=data.get('order_index', 0),
            is_active=True,
            created_by=current_user.username
        )
        db.session.add(entity_type)
        db.session.flush()
        
        # Create basic attributes if provided
        if 'attributes' in data:
            for i, attr_data in enumerate(data['attributes'], 1):
                attribute = AttributeDefinition(
                    entity_type_id=entity_type.id,
                    code=attr_data['code'],
                    name=attr_data['name'],
                    description=attr_data.get('description', ''),
                    data_type=DataTypeEnum(attr_data.get('data_type', 'VARCHAR')),
                    max_length=attr_data.get('max_length'),
                    is_required=attr_data.get('is_required', False),
                    is_unique=attr_data.get('is_unique', False),
                    order_index=i,
                    is_active=True,
                    created_by=current_user.username
                )
                db.session.add(attribute)
        
        db.session.commit()
        
        # Generate default forms
        EntityDesignerUtils.create_default_forms(entity_type.id)
        
        return jsonify({
            'success': True, 
            'entity_id': entity_type.id,
            'message': 'Entity created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500