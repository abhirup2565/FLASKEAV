# custom_admin/__init__.py
"""
Django-style Admin Interface for Flask - Simplified Version
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import inspect, func
from sqlalchemy.orm import joinedload
from models import *
import json
from datetime import datetime
from werkzeug.security import generate_password_hash
import math

# Create admin blueprint
admin_bp = Blueprint('custom_admin', __name__, url_prefix='/custom-admin', template_folder='templates')

class AdminConfig:
    """Central configuration for all admin models"""
    
    # Model registry with their configurations
    MODELS = {
        'application': {
            'model': Application,
            'name': 'Application',
            'name_plural': 'Applications',
            'icon': 'fas fa-cubes',
            'category': 'System',
            'list_display': ['code', 'name', 'order_index', 'is_active', 'created_at'],
            'list_filter': ['is_active', 'created_at'],
            'search_fields': ['code', 'name', 'description'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['order_index', 'name'],
            'form_fields': {
                'code': {'type': 'text', 'required': True, 'max_length': 50},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'icon': {'type': 'text', 'required': False, 'max_length': 100, 'help_text': 'Material icon name'},
                'order_index': {'type': 'number', 'required': False, 'default': 0},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },
        
        'module': {
            'model': Module,
            'name': 'Module',
            'name_plural': 'Modules',
            'icon': 'fas fa-folder',
            'category': 'System',
            'list_display': ['application', 'code', 'name', 'order_index', 'is_system', 'is_active'],
            'list_filter': ['application_id', 'is_system', 'is_active', 'created_at'],
            'search_fields': ['code', 'name', 'description'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['application_id', 'order_index', 'name'],
            'form_fields': {
                'application_id': {'type': 'select', 'required': True, 'source': 'application', 'display_field': 'name'},
                'code': {'type': 'text', 'required': True, 'max_length': 50},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'icon': {'type': 'text', 'required': False, 'max_length': 100},
                'order_index': {'type': 'number', 'required': False, 'default': 0},
                'is_system': {'type': 'checkbox', 'required': False, 'default': False},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },
        
        'entity_type': {
            'model': EntityType,
            'name': 'Entity Type',
            'name_plural': 'Entity Types',
            'icon': 'fas fa-table',
            'category': 'Entity Management',
            'list_display': ['module', 'code', 'name', 'is_master', 'is_transactional', 'is_active'],
            'list_filter': ['module_id', 'is_master', 'is_transactional', 'is_active'],
            'search_fields': ['code', 'name', 'description', 'table_name'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['module_id', 'order_index', 'name'],
            'form_fields': {
                'module_id': {'type': 'select', 'required': True, 'source': 'module', 'display_field': 'name'},
                'code': {'type': 'text', 'required': True, 'max_length': 50},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'table_name': {'type': 'text', 'required': False, 'max_length': 100},
                'is_master': {'type': 'checkbox', 'required': False, 'default': False},
                'is_transactional': {'type': 'checkbox', 'required': False, 'default': True},
                'icon': {'type': 'text', 'required': False, 'max_length': 100},
                'order_index': {'type': 'number', 'required': False, 'default': 0},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },
        
        'attribute_definition': {
            'model': AttributeDefinition,
            'name': 'Attribute Definition',
            'name_plural': 'Attribute Definitions',
            'icon': 'fas fa-list',
            'category': 'Entity Management',
            'list_display': ['entity_type', 'code', 'name', 'data_type', 'is_required', 'is_unique', 'is_active'],
            'list_filter': ['entity_type_id', 'data_type', 'is_required', 'is_unique', 'is_active'],
            'search_fields': ['code', 'name', 'description'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['entity_type_id', 'order_index', 'name'],
            'form_fields': {
                'entity_type_id': {'type': 'select', 'required': True, 'source': 'entity_type', 'display_field': 'name'},
                'code': {'type': 'text', 'required': True, 'max_length': 100},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'data_type': {'type': 'select', 'required': True, 'choices': [(e.value, e.value) for e in DataTypeEnum]},
                'max_length': {'type': 'number', 'required': False},
                'decimal_precision': {'type': 'number', 'required': False},
                'decimal_scale': {'type': 'number', 'required': False},
                'default_value': {'type': 'text', 'required': False},
                'is_required': {'type': 'checkbox', 'required': False, 'default': False},
                'is_unique': {'type': 'checkbox', 'required': False, 'default': False},
                'is_indexed': {'type': 'checkbox', 'required': False, 'default': False},
                'validation_rules': {'type': 'json', 'required': False},
                'order_index': {'type': 'number', 'required': False, 'default': 0},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },
        
        'form_definition': {
            'model': FormDefinition,
            'name': 'Form Definition',
            'name_plural': 'Form Definitions',
            'icon': 'fas fa-edit',
            'category': 'Form Management',
            'list_display': ['entity_type', 'code', 'name', 'form_type', 'layout_type', 'is_default', 'is_active'],
            'list_filter': ['entity_type_id', 'form_type', 'layout_type', 'is_default', 'is_active'],
            'search_fields': ['code', 'name', 'description'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['entity_type_id', 'form_type'],
            'form_fields': {
                'entity_type_id': {'type': 'select', 'required': True, 'source': 'entity_type', 'display_field': 'name'},
                'code': {'type': 'text', 'required': True, 'max_length': 100},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'form_type': {'type': 'select', 'required': True, 'choices': [(e.value, e.value) for e in FormTypeEnum]},
                'layout_type': {'type': 'select', 'required': False, 'choices': [(e.value, e.value) for e in LayoutTypeEnum]},
                'records_per_page': {'type': 'number', 'required': False, 'default': 10},
                'pages_per_load': {'type': 'number', 'required': False, 'default': 1},
                'allow_inline_edit': {'type': 'checkbox', 'required': False, 'default': False},
                'show_attachment_count': {'type': 'checkbox', 'required': False, 'default': False},
                'mandatory_confirmation': {'type': 'checkbox', 'required': False, 'default': False},
                'is_default': {'type': 'checkbox', 'required': False, 'default': False},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },
        
        'form_field_configuration': {
            'model': FormFieldConfiguration,
            'name': 'Form Field Configuration',
            'name_plural': 'Form Field Configurations',
            'icon': 'fas fa-wpforms',
            'category': 'Form Management',
            'list_display': ['form_definition', 'attribute_definition', 'field_label', 'field_type', 'is_visible', 'is_required', 'order_index'],
            'list_filter': ['form_definition_id', 'field_type', 'is_visible', 'is_required', 'is_editable'],
            'search_fields': ['field_label'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['form_definition_id', 'order_index'],
            'form_fields': {
                'form_definition_id': {'type': 'select', 'required': True, 'source': 'form_definition', 'display_field': 'name'},
                'attribute_definition_id': {'type': 'select', 'required': True, 'source': 'attribute_definition', 'display_field': 'name'},
                'field_label': {'type': 'text', 'required': False, 'max_length': 255},
                'field_type': {'type': 'select', 'required': True, 'choices': [(e.value, e.value) for e in FieldTypeEnum]},
                'placeholder_text': {'type': 'text', 'required': False, 'max_length': 255},
                'help_text': {'type': 'textarea', 'required': False},
                'order_index': {'type': 'number', 'required': False, 'default': 0},
                'grid_column_span': {'type': 'number', 'required': False, 'default': 1, 'min': 1, 'max': 12},
                'grid_row_span': {'type': 'number', 'required': False, 'default': 1, 'min': 1, 'max': 6},
                # NEW: Simplified dropdown configuration
                'dropdown_source_entity_id': {'type': 'select', 'required': False, 'source': 'entity_type', 'display_field': 'name'},
                'dropdown_source_attribute_id': {'type': 'select', 'required': False, 'source': 'attribute_definition', 'display_field': 'name'},
                'dropdown_display_attribute_id': {'type': 'select', 'required': False, 'source': 'attribute_definition', 'display_field': 'name'},
                'show_unique_values_only': {'type': 'checkbox', 'required': False, 'default': False},
                'is_visible': {'type': 'checkbox', 'required': False, 'default': True},
                'is_editable': {'type': 'checkbox', 'required': False, 'default': True},
                'is_required': {'type': 'checkbox', 'required': False, 'default': False},
                'is_searchable': {'type': 'checkbox', 'required': False, 'default': False},
                'is_sortable': {'type': 'checkbox', 'required': False, 'default': False},
                'conditional_visibility_rules': {'type': 'json', 'required': False},
                'conditional_requirement_rules': {'type': 'json', 'required': False},
                'conditional_editability_rules': {'type': 'json', 'required': False},
                'validation_rules': {'type': 'json', 'required': False},
                'css_classes': {'type': 'text', 'required': False, 'max_length': 500},
                'custom_attributes': {'type': 'json', 'required': False},
            }
        },

        'entity_instance': {
            'model': EntityInstance,
            'name': 'Entity Instance',
            'name_plural': 'Entity Instances',
            'icon': 'fas fa-database',
            'category': 'Entity Management',
            'list_display': ['entity_type', 'instance_code', 'workflow_status', 'is_active', 'created_at'],
            'list_filter': ['entity_type_id', 'workflow_status', 'is_active'],
            'search_fields': ['instance_code'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['entity_type_id', 'created_at'],
            'form_fields': {
                'entity_type_id': {'type': 'select', 'required': True, 'source': 'entity_type', 'display_field': 'name'},
                'instance_code': {'type': 'text', 'required': False, 'max_length': 255},
                'workflow_status': {'type': 'text', 'required': False, 'max_length': 100},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'user': {
            'model': User,
            'name': 'User',
            'name_plural': 'Users',
            'icon': 'fas fa-users',
            'category': 'Security',
            'list_display': ['username', 'email', 'full_name', 'is_active', 'last_login', 'created_at'],
            'list_filter': ['is_active', 'last_login', 'created_at'],
            'search_fields': ['username', 'email', 'first_name', 'last_name'],
            'readonly_fields': ['last_login', 'created_at', 'updated_at'],
            'ordering': ['username'],
            'form_fields': {
                'username': {'type': 'text', 'required': True, 'max_length': 100},
                'email': {'type': 'email', 'required': True, 'max_length': 255},
                'first_name': {'type': 'text', 'required': False, 'max_length': 100},
                'last_name': {'type': 'text', 'required': False, 'max_length': 100},
                'password': {'type': 'password', 'required': False, 'help_text': 'Leave blank to keep current password'},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'role': {
            'model': Role,
            'name': 'Role',
            'name_plural': 'Roles',
            'icon': 'fas fa-shield-alt',
            'category': 'Security',
            'list_display': ['code', 'name', 'is_system', 'is_active', 'created_at'],
            'list_filter': ['is_system', 'is_active'],
            'search_fields': ['code', 'name', 'description'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['name'],
            'form_fields': {
                'code': {'type': 'text', 'required': True, 'max_length': 100},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'is_system': {'type': 'checkbox', 'required': False, 'default': False},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'user_role': {
            'model': UserRole,
            'name': 'User Role',
            'name_plural': 'User Roles',
            'icon': 'fas fa-user-shield',
            'category': 'Security',
            'list_display': ['user', 'role', 'created_at'],
            'list_filter': ['user_id', 'role_id'],
            'search_fields': [],
            'readonly_fields': ['created_at'],
            'ordering': ['user_id', 'role_id'],
            'form_fields': {
                'user_id': {'type': 'select', 'required': True, 'source': 'user', 'display_field': 'username'},
                'role_id': {'type': 'select', 'required': True, 'source': 'role', 'display_field': 'name'},
            }
        },

        'entity_permission': {
            'model': EntityPermission,
            'name': 'Entity Permission',
            'name_plural': 'Entity Permissions',
            'icon': 'fas fa-lock',
            'category': 'Security',
            'list_display': ['role', 'entity_type', 'can_read', 'can_create', 'can_update', 'can_delete'],
            'list_filter': ['role_id', 'entity_type_id', 'can_read', 'can_create', 'can_update', 'can_delete'],
            'search_fields': [],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['role_id', 'entity_type_id'],
            'form_fields': {
                'role_id': {'type': 'select', 'required': True, 'source': 'role', 'display_field': 'name'},
                'entity_type_id': {'type': 'select', 'required': True, 'source': 'entity_type', 'display_field': 'name'},
                'can_read': {'type': 'checkbox', 'required': False, 'default': False},
                'can_create': {'type': 'checkbox', 'required': False, 'default': False},
                'can_update': {'type': 'checkbox', 'required': False, 'default': False},
                'can_delete': {'type': 'checkbox', 'required': False, 'default': False},
                'field_level_permissions': {'type': 'json', 'required': False},
                'row_level_conditions': {'type': 'json', 'required': False},
            }
        },

        'user_favorite_module': {
            'model': UserFavoriteModule,
            'name': 'User Favorite Module',
            'name_plural': 'User Favorite Modules',
            'icon': 'fas fa-star',
            'category': 'Security',
            'list_display': ['user', 'module', 'order_index', 'created_at'],
            'list_filter': ['user_id', 'module_id'],
            'search_fields': [],
            'readonly_fields': ['created_at'],
            'ordering': ['user_id', 'order_index'],
            'form_fields': {
                'user_id': {'type': 'select', 'required': True, 'source': 'user', 'display_field': 'username'},
                'module_id': {'type': 'select', 'required': True, 'source': 'module', 'display_field': 'name'},
                'order_index': {'type': 'number', 'required': False, 'default': 0},
            }
        },

        'workflow_state': {
            'model': WorkflowState,
            'name': 'Workflow State',
            'name_plural': 'Workflow States',
            'icon': 'fas fa-circle',
            'category': 'Workflow',
            'list_display': ['entity_type', 'code', 'name', 'is_initial', 'is_final', 'color', 'order_index'],
            'list_filter': ['entity_type_id', 'is_initial', 'is_final', 'is_active'],
            'search_fields': ['code', 'name'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['entity_type_id', 'order_index'],
            'form_fields': {
                'entity_type_id': {'type': 'select', 'required': True, 'source': 'entity_type', 'display_field': 'name'},
                'code': {'type': 'text', 'required': True, 'max_length': 100},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'is_initial': {'type': 'checkbox', 'required': False, 'default': False},
                'is_final': {'type': 'checkbox', 'required': False, 'default': False},
                'color': {'type': 'text', 'required': False, 'max_length': 7, 'placeholder': '#ffffff'},
                'order_index': {'type': 'number', 'required': False, 'default': 0},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'workflow_transition': {
            'model': WorkflowTransition,
            'name': 'Workflow Transition',
            'name_plural': 'Workflow Transitions',
            'icon': 'fas fa-arrow-right',
            'category': 'Workflow',
            'list_display': ['from_state', 'to_state', 'action_name', 'action_code', 'is_active'],
            'list_filter': ['from_state_id', 'to_state_id', 'is_active'],
            'search_fields': ['action_name', 'action_code'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['from_state_id', 'to_state_id'],
            'form_fields': {
                'from_state_id': {'type': 'select', 'required': True, 'source': 'workflow_state', 'display_field': 'name'},
                'to_state_id': {'type': 'select', 'required': True, 'source': 'workflow_state', 'display_field': 'name'},
                'action_name': {'type': 'text', 'required': True, 'max_length': 255},
                'action_code': {'type': 'text', 'required': True, 'max_length': 100},
                'conditions': {'type': 'json', 'required': False},
                'required_roles': {'type': 'json', 'required': False},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'event_configuration': {
            'model': EventConfiguration,
            'name': 'Event Configuration',
            'name_plural': 'Event Configurations',
            'icon': 'fas fa-bolt',
            'category': 'Workflow',
            'list_display': ['entity_type', 'event_type', 'event_name', 'event_code', 'is_active'],
            'list_filter': ['entity_type_id', 'event_type', 'is_active'],
            'search_fields': ['event_name', 'event_code'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['entity_type_id', 'event_type'],
            'form_fields': {
                'entity_type_id': {'type': 'select', 'required': True, 'source': 'entity_type', 'display_field': 'name'},
                'event_type': {'type': 'select', 'required': True, 'choices': [(e.value, e.value) for e in EventTypeEnum]},
                'event_name': {'type': 'text', 'required': True, 'max_length': 255},
                'event_code': {'type': 'text', 'required': True, 'max_length': 100},
                'conditions': {'type': 'json', 'required': False},
                'actions': {'type': 'json', 'required': False},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'approval_type': {
            'model': ApprovalType,
            'name': 'Approval Type',
            'name_plural': 'Approval Types',
            'icon': 'fas fa-check-circle',
            'category': 'Approval',
            'list_display': ['code', 'name', 'is_active', 'created_at'],
            'list_filter': ['is_active'],
            'search_fields': ['code', 'name', 'description'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['name'],
            'form_fields': {
                'code': {'type': 'text', 'required': True, 'max_length': 100},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'description': {'type': 'textarea', 'required': False},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'organizational_unit': {
            'model': OrganizationalUnit,
            'name': 'Organizational Unit',
            'name_plural': 'Organizational Units',
            'icon': 'fas fa-sitemap',
            'category': 'Approval',
            'list_display': ['code', 'name', 'unit_type', 'parent_unit', 'manager', 'level_order', 'is_active'],
            'list_filter': ['unit_type', 'is_active'],
            'search_fields': ['code', 'name', 'description'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['level_order', 'name'],
            'form_fields': {
                'parent_unit_id': {'type': 'select', 'required': False, 'source': 'organizational_unit', 'display_field': 'name'},
                'code': {'type': 'text', 'required': True, 'max_length': 100},
                'name': {'type': 'text', 'required': True, 'max_length': 255},
                'unit_type': {'type': 'select', 'required': True, 'choices': [(e.value, e.value) for e in UnitTypeEnum]},
                'manager_user_id': {'type': 'select', 'required': False, 'source': 'user', 'display_field': 'username'},
                'description': {'type': 'textarea', 'required': False},
                'level_order': {'type': 'number', 'required': False, 'default': 0},
                'is_active': {'type': 'checkbox', 'required': False, 'default': True},
            }
        },

        'user_organizational_assignment': {
            'model': UserOrganizationalAssignment,
            'name': 'User Organizational Assignment',
            'name_plural': 'User Organizational Assignments',
            'icon': 'fas fa-user-cog',
            'category': 'Approval',
            'list_display': ['user', 'organizational_unit', 'position_title', 'is_primary', 'is_manager', 'effective_from'],
            'list_filter': ['organizational_unit_id', 'is_primary', 'is_manager'],
            'search_fields': ['position_title'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['user_id', 'organizational_unit_id'],
            'form_fields': {
                'user_id': {'type': 'select', 'required': True, 'source': 'user', 'display_field': 'username'},
                'organizational_unit_id': {'type': 'select', 'required': True, 'source': 'organizational_unit', 'display_field': 'name'},
                'position_title': {'type': 'text', 'required': False, 'max_length': 255},
                'is_primary': {'type': 'checkbox', 'required': False, 'default': True},
                'is_manager': {'type': 'checkbox', 'required': False, 'default': False},
                'effective_from': {'type': 'date', 'required': True},
                'effective_to': {'type': 'date', 'required': False},
            }
        },

        'audit_log': {
            'model': AuditLog,
            'name': 'Audit Log',
            'name_plural': 'Audit Logs',
            'icon': 'fas fa-history',
            'category': 'Audit',
            'list_display': ['entity_type', 'entity_instance', 'operation', 'user', 'ip_address', 'created_at'],
            'list_filter': ['entity_type_id', 'operation', 'user_id', 'created_at'],
            'search_fields': ['ip_address'],
            'readonly_fields': ['created_at'],
            'ordering': ['-created_at'],
            'form_fields': {
                'entity_type_id': {'type': 'select', 'required': False, 'source': 'entity_type', 'display_field': 'name'},
                'entity_instance_id': {'type': 'number', 'required': False},
                'operation': {'type': 'select', 'required': True, 'choices': [(e.value, e.value) for e in OperationEnum]},
                'old_values': {'type': 'json', 'required': False},
                'new_values': {'type': 'json', 'required': False},
                'user_id': {'type': 'select', 'required': False, 'source': 'user', 'display_field': 'username'},
                'ip_address': {'type': 'text', 'required': False, 'max_length': 45},
                'user_agent': {'type': 'textarea', 'required': False},
            }
        },

        'system_parameter': {
            'model': SystemParameter,
            'name': 'System Parameter',
            'name_plural': 'System Parameters',
            'icon': 'fas fa-cogs',
            'category': 'System',
            'list_display': ['category', 'param_key', 'param_value', 'data_type', 'is_encrypted'],
            'list_filter': ['category', 'data_type', 'is_encrypted'],
            'search_fields': ['category', 'param_key', 'param_value'],
            'readonly_fields': ['created_at', 'updated_at'],
            'ordering': ['category', 'param_key'],
            'form_fields': {
                'category': {'type': 'text', 'required': True, 'max_length': 100},
                'param_key': {'type': 'text', 'required': True, 'max_length': 255},
                'param_value': {'type': 'textarea', 'required': False},
                'data_type': {'type': 'select', 'required': False, 'choices': [(e.value, e.value) for e in SystemParameterDataTypeEnum]},
                'description': {'type': 'textarea', 'required': False},
                'is_encrypted': {'type': 'checkbox', 'required': False, 'default': False},
            }
        },
    }
    
    # Categories for navigation - SIMPLIFIED
    CATEGORIES = {
        'System': {'icon': 'fas fa-cogs', 'order': 1},
        'Entity Management': {'icon': 'fas fa-database', 'order': 2},
        'Form Management': {'icon': 'fas fa-edit', 'order': 3},
        'Security': {'icon': 'fas fa-shield-alt', 'order': 4},
        'Workflow': {'icon': 'fas fa-project-diagram', 'order': 5},
        'Approval': {'icon': 'fas fa-check-circle', 'order': 6},
        'Audit': {'icon': 'fas fa-history', 'order': 7},
    }
    
    @classmethod
    def get_model_config(cls, model_key):
        """Get configuration for a specific model"""
        return cls.MODELS.get(model_key, {})
    
    @classmethod
    def get_navigation_structure(cls):
        """Get structured navigation for admin interface"""
        navigation = {}
        for model_key, config in cls.MODELS.items():
            category = config.get('category', 'Other')
            if category not in navigation:
                navigation[category] = {
                    'models': [],
                    'icon': cls.CATEGORIES.get(category, {}).get('icon', 'fas fa-folder'),
                    'order': cls.CATEGORIES.get(category, {}).get('order', 999)
                }
            navigation[category]['models'].append({
                'key': model_key,
                'name': config['name_plural'],
                'icon': config['icon'],
                'url': url_for('custom_admin.model_list', model_name=model_key)
            })
        
        # Sort categories by order
        return dict(sorted(navigation.items(), key=lambda x: x[1]['order']))
    
    @classmethod
    def get_choices_for_field(cls, model_key, field_name):
        """Get choices for select fields"""
        config = cls.get_model_config(model_key)
        field_config = config.get('form_fields', {}).get(field_name, {})
        
        if 'choices' in field_config:
            return field_config['choices']
        
        if 'source' in field_config:
            source_model_key = field_config['source']
            source_config = cls.get_model_config(source_model_key)
            if source_config:
                source_model = source_config['model']
                display_field = field_config.get('display_field', 'name')
                
                # Get all active records
                query = source_model.query
                if hasattr(source_model, 'is_active'):
                    query = query.filter_by(is_active=True)
                
                records = query.all()
                choices = []
                for record in records:
                    display_value = getattr(record, display_field, str(record.id))
                    # For nested displays like "module.application.name - module.name"
                    if hasattr(record, 'module') and hasattr(record.module, 'application'):
                        display_value = f"{record.module.application.name} - {display_value}"
                    choices.append((record.id, display_value))
                
                return choices
        
        return []

class AdminUtils:
    """Utility functions for admin operations"""
    
    @staticmethod
    def get_model_by_name(model_name):
        """Get model class by name"""
        config = AdminConfig.get_model_config(model_name)
        return config.get('model') if config else None
    
    @staticmethod
    def get_relationship_count(obj, relationship_name):
        """Safely get the count of related objects"""
        try:
            relationship = getattr(obj, relationship_name, None)
            if relationship is None:
                return 0
            
            if hasattr(relationship, 'count'):
                return relationship.count()
            
            if hasattr(relationship, '__len__'):
                return len(relationship)
            
            if relationship:
                return 1
            
            return 0
        except Exception as e:
            print(f"Error getting relationship count for {relationship_name}: {e}")
            return 0
    
    @staticmethod
    def get_display_value(obj, field_name):
        """Get display value for a field, handling relationships"""
        if not obj:
            return ''
        
        try:
            # Handle nested attributes like 'module.application.name'
            if '.' in field_name:
                parts = field_name.split('.')
                value = obj
                for part in parts:
                    if value is None:
                        break
                    value = getattr(value, part, None)
                return str(value) if value is not None else ''
            
            # Handle direct attributes
            value = getattr(obj, field_name, None)
            
            # Special handling for foreign key relationships
            if hasattr(obj.__class__, field_name):
                attr = getattr(obj.__class__, field_name)
                if hasattr(attr.property, 'mapper'):  # It's a relationship
                    related_obj = getattr(obj, field_name)
                    if related_obj:
                        # Try to get name, then code, then id
                        for attr_name in ['name', 'code', 'title', 'username']:
                            if hasattr(related_obj, attr_name):
                                return getattr(related_obj, attr_name)
                        return str(related_obj.id)
                    return ''
            
            # Handle special field types
            if isinstance(value, bool):
                return 'Yes' if value else 'No'
            elif isinstance(value, datetime):
                return value.strftime('%Y-%m-%d %H:%M')
            elif value is None:
                return ''
            
            return str(value)
            
        except Exception as e:
            return f'Error: {str(e)}'
    
    @staticmethod
    def apply_filters(query, model_config, filters):
        """Apply filters to query"""
        model = model_config['model']
        
        for field_name, value in filters.items():
            if not value:
                continue
                
            if hasattr(model, field_name):
                field = getattr(model, field_name)
                
                # Handle different filter types
                if isinstance(value, str) and value.strip():
                    if 'date' in field_name.lower():
                        # Date filtering
                        try:
                            date_value = datetime.strptime(value, '%Y-%m-%d')
                            query = query.filter(field >= date_value)
                        except ValueError:
                            pass
                    else:
                        # Text filtering
                        query = query.filter(field.ilike(f'%{value}%'))
                elif isinstance(value, bool) or value in ['true', 'false']:
                    bool_value = value if isinstance(value, bool) else value.lower() == 'true'
                    query = query.filter(field == bool_value)
                else:
                    query = query.filter(field == value)
        
        return query
    
    @staticmethod
    def apply_search(query, model_config, search_term):
        """Apply search to query"""
        if not search_term:
            return query
        
        model = model_config['model']
        search_fields = model_config.get('search_fields', [])
        
        if not search_fields:
            return query
        
        # Build OR conditions for search fields
        conditions = []
        for field_name in search_fields:
            if hasattr(model, field_name):
                field = getattr(model, field_name)
                conditions.append(field.ilike(f'%{search_term}%'))
        
        if conditions:
            from sqlalchemy import or_
            query = query.filter(or_(*conditions))
        
        return query
    
    @staticmethod
    def get_field_value_for_form(obj, field_name, field_config):
        """Get the appropriate value for a form field, handling foreign keys and enums properly"""
        if not obj or not hasattr(obj, field_name):
            return None
            
        value = getattr(obj, field_name)
        
        # Handle select fields (foreign keys)
        if field_config.get('type') == 'select':
            # Check if this is an enum field by looking at the choices
            choices = field_config.get('choices', [])
            if choices:
                # This is an enum field, extract the enum value
                if hasattr(value, 'value'):
                    return value.value
                elif hasattr(value, 'name'):
                    return value.name
                else:
                    return value
            else:
                # This is a foreign key field
                if field_config.get('source'):
                    if field_name.endswith('_id'):
                        return value
                    else:
                        if value and hasattr(value, 'id'):
                            return value.id
                        return value
        
        # Handle JSON fields
        elif isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)
        
        # Handle datetime fields
        elif hasattr(value, 'strftime'):
            return value
            
        # Handle enum fields that aren't select fields
        elif hasattr(value, 'value'):
            return value.value
        elif hasattr(value, 'name'):
            return value.name
            
        # Default case
        return value

# ROUTES START HERE

@admin_bp.route('/')
@login_required
def dashboard():
    """Admin dashboard with statistics"""
    stats = {}
    
    # Calculate statistics for each model
    for model_key, config in AdminConfig.MODELS.items():
        model = config['model']
        try:
            total_count = model.query.count()
            active_count = 0
            if hasattr(model, 'is_active'):
                active_count = model.query.filter_by(is_active=True).count()
            
            stats[model_key] = {
                'name': config['name_plural'],
                'icon': config['icon'],
                'total': total_count,
                'active': active_count,
                'category': config.get('category', 'Other'),
                'url': url_for('custom_admin.model_list', model_name=model_key)
            }
        except Exception as e:
            print(f"Error calculating stats for {model_key}: {e}")
            stats[model_key] = {
                'name': config['name_plural'],
                'icon': config['icon'],
                'total': 0,
                'active': 0,
                'category': config.get('category', 'Other'),
                'url': url_for('custom_admin.model_list', model_name=model_key)
            }
    
    # Get navigation structure
    navigation = AdminConfig.get_navigation_structure()
    
    # Recent activities
    recent_activities = []
    try:
        if AuditLog.query.first():
            recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
            for log in recent_logs:
                recent_activities.append({
                    'action': f"{log.operation.value} {log.entity_type.name if log.entity_type else 'Unknown'}",
                    'user': log.user.username if log.user else 'System',
                    'time': log.created_at,
                    'ip': log.ip_address
                })
    except Exception as e:
        print(f"Error loading recent activities: {e}")
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         navigation=navigation,
                         recent_activities=recent_activities)

@admin_bp.route('/models/<model_name>')
@login_required
def model_list(model_name):
    """Generic model list view"""
    config = AdminConfig.get_model_config(model_name)
    if not config:
        flash(f'Model {model_name} not found', 'error')
        return redirect(url_for('custom_admin.dashboard'))
    
    model = config['model']
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 25, type=int)
    
    # Get filters and search
    filters = {}
    search_term = request.args.get('search', '').strip()
    
    # Build base query
    query = model.query
    
    # Apply eager loading for relationships to avoid N+1 queries
    list_display = config.get('list_display', [])
    for field in list_display:
        if '.' in field:  # Relationship field
            rel_name = field.split('.')[0]
            if hasattr(model, rel_name):
                query = query.options(joinedload(getattr(model, rel_name)))
    
    # Apply filters
    for filter_field in config.get('list_filter', []):
        filter_value = request.args.get(f'filter_{filter_field}')
        if filter_value:
            filters[filter_field] = filter_value
    
    query = AdminUtils.apply_filters(query, config, filters)
    
    # Apply search
    query = AdminUtils.apply_search(query, config, search_term)
    
    # Apply ordering
    ordering = config.get('ordering', ['id'])
    for order_field in ordering:
        if hasattr(model, order_field):
            query = query.order_by(getattr(model, order_field))
    
    # Get total count for statistics
    total_count = query.count()
    
    # Apply pagination
    try:
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        objects = pagination.items
    except Exception as e:
        flash(f'Error loading data: {str(e)}', 'error')
        objects = []
        pagination = None
    
    # Get filter choices for dropdowns
    filter_choices = {}
    for filter_field in config.get('list_filter', []):
        if hasattr(model, filter_field):
            field = getattr(model, filter_field)
            
            # For foreign key fields, get related objects
            if hasattr(field.property, 'mapper'):
                related_model = field.property.mapper.class_
                choices = related_model.query.all()
                filter_choices[filter_field] = [(obj.id, str(getattr(obj, 'name', obj.id))) for obj in choices]
            # For boolean fields
            elif hasattr(field.type, 'python_type') and field.type.python_type == bool:
                filter_choices[filter_field] = [(True, 'Yes'), (False, 'No')]
            # For enum fields
            elif hasattr(field.type, 'enums'):
                filter_choices[filter_field] = [(enum, enum) for enum in field.type.enums]
    
    # Get navigation structure
    navigation = AdminConfig.get_navigation_structure()
    
    return render_template('admin/model_list.html',
                         config=config,
                         model_name=model_name,
                         objects=objects,
                         pagination=pagination,
                         total_count=total_count,
                         search_term=search_term,
                         filters=filters,
                         filter_choices=filter_choices,
                         navigation=navigation)

@admin_bp.route('/models/<model_name>/create', methods=['GET', 'POST'])
@login_required
def model_create(model_name):
    """Generic model create view"""
    config = AdminConfig.get_model_config(model_name)
    if not config:
        flash(f'Model {model_name} not found', 'error')
        return redirect(url_for('custom_admin.dashboard'))
    
    model = config['model']
    
    if request.method == 'POST':
        try:
            # Create new instance
            instance = model()
            
            # Set form fields
            form_fields = config.get('form_fields', {})
            for field_name, field_config in form_fields.items():
                field_value = request.form.get(field_name)
                
                # Handle different field types
                if field_config['type'] == 'checkbox':
                    field_value = bool(field_value)
                elif field_config['type'] == 'number':
                    field_value = int(field_value) if field_value else (field_config.get('default', 0) if field_config.get('required') else None)
                elif field_config['type'] == 'select' and field_value:
                    field_value = int(field_value)
                elif field_config['type'] == 'password' and field_value:
                    field_value = generate_password_hash(field_value)
                elif field_config['type'] == 'json' and field_value:
                    try:
                        field_value = json.loads(field_value)
                    except json.JSONDecodeError:
                        field_value = None
                elif not field_value and field_config.get('default') is not None:
                    field_value = field_config['default']
                
                # Skip readonly fields and empty non-required fields
                if field_name in config.get('readonly_fields', []):
                    continue
                
                if hasattr(instance, field_name):
                    setattr(instance, field_name, field_value)
            
            # Set audit fields
            if hasattr(instance, 'created_by'):
                instance.created_by = current_user.username
            if hasattr(instance, 'updated_by'):
                instance.updated_by = current_user.username
            
            # Save to database
            db.session.add(instance)
            db.session.commit()
            
            flash(f'{config["name"]} created successfully!', 'success')
            return redirect(url_for('custom_admin.model_list', model_name=model_name))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating {config["name"]}: {str(e)}', 'error')
    
    # Get form choices for select fields
    form_choices = {}
    form_fields = config.get('form_fields', {})
    for field_name, field_config in form_fields.items():
        if field_config['type'] == 'select':
            choices = AdminConfig.get_choices_for_field(model_name, field_name)
            form_choices[field_name] = choices
    
    navigation = AdminConfig.get_navigation_structure()
    
    return render_template('admin/model_form.html',
                         config=config,
                         model_name=model_name,
                         instance=None,
                         form_choices=form_choices,
                         navigation=navigation,
                         action='create')

@admin_bp.route('/models/<model_name>/<int:object_id>')
@login_required
def model_detail(model_name, object_id):
    """Generic model detail view"""
    config = AdminConfig.get_model_config(model_name)
    if not config:
        flash(f'Model {model_name} not found', 'error')
        return redirect(url_for('custom_admin.dashboard'))
    
    model = config['model']
    instance = model.query.get_or_404(object_id)
    
    # Get all fields for display
    inspector = inspect(model)
    all_fields = []
    
    # Add regular columns
    for column in inspector.columns:
        if column.name not in config.get('readonly_fields', []):
            all_fields.append({
                'name': column.name,
                'label': column.name.replace('_', ' ').title(),
                'value': AdminUtils.get_display_value(instance, column.name),
                'type': str(column.type)
            })
    
    # Add relationships
    for relationship in inspector.relationships:
        if relationship.direction.name == 'MANYTOONE':  # Foreign key relationships
            all_fields.append({
                'name': relationship.key,
                'label': relationship.key.replace('_', ' ').title(),
                'value': AdminUtils.get_display_value(instance, relationship.key),
                'type': 'relationship'
            })
    
    navigation = AdminConfig.get_navigation_structure()
    
    return render_template('admin/model_detail.html',
                         config=config,
                         model_name=model_name,
                         instance=instance,
                         all_fields=all_fields,
                         navigation=navigation)

@admin_bp.route('/models/<model_name>/<int:object_id>/edit', methods=['GET', 'POST'])
@login_required
def model_edit(model_name, object_id):
    """Generic model edit view"""
    config = AdminConfig.get_model_config(model_name)
    if not config:
        flash(f'Model {model_name} not found', 'error')
        return redirect(url_for('custom_admin.dashboard'))
    
    model = config['model']
    instance = model.query.get_or_404(object_id)
    
    if request.method == 'POST':
        try:
            # Update form fields
            form_fields = config.get('form_fields', {})
            for field_name, field_config in form_fields.items():
                # Skip readonly fields
                if field_name in config.get('readonly_fields', []):
                    continue
                
                field_value = request.form.get(field_name)
                
                # Handle different field types
                if field_config['type'] == 'checkbox':
                    field_value = bool(field_value)
                elif field_config['type'] == 'number':
                    field_value = int(field_value) if field_value else None
                elif field_config['type'] == 'select' and field_value:
                    # Check if this is an enum field
                    choices = field_config.get('choices', [])
                    if choices:
                        # This is an enum field, convert string back to enum
                        if hasattr(model, field_name):
                            column = getattr(model.__table__.columns, field_name, None)
                            if column is not None and hasattr(column.type, 'enum_class'):
                                enum_class = column.type.enum_class
                                for enum_val in enum_class:
                                    if enum_val.value == field_value:
                                        field_value = enum_val
                                        break
                    else:
                        # Regular foreign key field
                        field_value = int(field_value)
                elif field_config['type'] == 'password':
                    # Only update password if provided
                    if field_value:
                        field_value = generate_password_hash(field_value)
                    else:
                        continue
                elif field_config['type'] == 'json' and field_value:
                    try:
                        field_value = json.loads(field_value)
                    except json.JSONDecodeError:
                        field_value = None
                
                if hasattr(instance, field_name):
                    setattr(instance, field_name, field_value)
            
            # Set audit fields
            if hasattr(instance, 'updated_by'):
                instance.updated_by = current_user.username
            if hasattr(instance, 'updated_at'):
                instance.updated_at = datetime.utcnow()
            
            # Save to database
            db.session.commit()
            
            flash(f'{config["name"]} updated successfully!', 'success')
            return redirect(url_for('custom_admin.model_detail', model_name=model_name, object_id=object_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating {config["name"]}: {str(e)}', 'error')
    
    # Get current values for form
    current_values = {}
    form_fields = config.get('form_fields', {})
    
    for field_name, field_config in form_fields.items():
        current_values[field_name] = AdminUtils.get_field_value_for_form(instance, field_name, field_config)
    
    # Get form choices for select fields
    form_choices = {}
    for field_name, field_config in form_fields.items():
        if field_config['type'] == 'select':
            choices = AdminConfig.get_choices_for_field(model_name, field_name)
            form_choices[field_name] = choices
    
    navigation = AdminConfig.get_navigation_structure()
    
    return render_template('admin/model_form.html',
                         config=config,
                         model_name=model_name,
                         instance=instance,
                         current_values=current_values,
                         form_choices=form_choices,
                         navigation=navigation,
                         action='edit')

@admin_bp.route('/models/<model_name>/<int:object_id>/delete', methods=['POST'])
@login_required
def model_delete(model_name, object_id):
    """Generic model delete view"""
    config = AdminConfig.get_model_config(model_name)
    if not config:
        flash(f'Model {model_name} not found', 'error')
        return redirect(url_for('custom_admin.dashboard'))
    
    model = config['model']
    instance = model.query.get_or_404(object_id)
    
    try:
        # Check for dependencies using the safe count method
        inspector = inspect(model)
        dependencies = []
        
        for relationship in inspector.relationships:
            if relationship.direction.name == 'ONETOMANY':
                # Use the safe count method from AdminUtils
                count = AdminUtils.get_relationship_count(instance, relationship.key)
                
                if count > 0:
                    dependencies.append(f'{relationship.key}: {count} records')
        
        if dependencies:
            flash(f'Cannot delete {config["name"]}. Dependencies found: {", ".join(dependencies)}', 'error')
            return redirect(url_for('custom_admin.model_detail', model_name=model_name, object_id=object_id))
        
        # Delete the instance
        db.session.delete(instance)
        db.session.commit()
        
        flash(f'{config["name"]} deleted successfully!', 'success')
        return redirect(url_for('custom_admin.model_list', model_name=model_name))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting {config["name"]}: {str(e)}', 'error')
        return redirect(url_for('custom_admin.model_detail', model_name=model_name, object_id=object_id))

# API endpoints for AJAX operations
@admin_bp.route('/api/models/<model_name>/choices/<field_name>')
@login_required
def get_field_choices(model_name, field_name):
    """Get choices for a specific field via AJAX"""
    try:
        choices = AdminConfig.get_choices_for_field(model_name, field_name)
        return jsonify(choices)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/models/<model_name>/bulk-action', methods=['POST'])
@login_required
def bulk_action(model_name):
    """Handle bulk actions on multiple objects"""
    config = AdminConfig.get_model_config(model_name)
    if not config:
        return jsonify({'error': 'Model not found'}), 404
    
    model = config['model']
    action = request.json.get('action')
    object_ids = request.json.get('object_ids', [])
    
    if not action or not object_ids:
        return jsonify({'error': 'Action and object IDs required'}), 400
    
    try:
        objects = model.query.filter(model.id.in_(object_ids)).all()
        
        if action == 'delete':
            for obj in objects:
                db.session.delete(obj)
            db.session.commit()
            return jsonify({'message': f'Deleted {len(objects)} records'})
        
        elif action == 'activate' and hasattr(model, 'is_active'):
            for obj in objects:
                obj.is_active = True
            db.session.commit()
            return jsonify({'message': f'Activated {len(objects)} records'})
        
        elif action == 'deactivate' and hasattr(model, 'is_active'):
            for obj in objects:
                obj.is_active = False
            db.session.commit()
            return jsonify({'message': f'Deactivated {len(objects)} records'})
        
        else:
            return jsonify({'error': 'Unknown action'}), 400
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Template context processors and filters
@admin_bp.context_processor
def admin_context():
    """Add common variables to admin templates"""
    return {
        'admin_navigation': AdminConfig.get_navigation_structure(),
        'admin_utils': AdminUtils,
        'current_time': datetime.utcnow()
    }

@admin_bp.app_template_filter('admin_display_value')
def admin_display_value_filter(obj, field_name):
    """Template filter to get display value for any field"""
    return AdminUtils.get_display_value(obj, field_name)

@admin_bp.app_template_filter('relationship_count')
def relationship_count_filter(obj, relationship_name):
    """Template filter to safely get relationship count"""
    return AdminUtils.get_relationship_count(obj, relationship_name)