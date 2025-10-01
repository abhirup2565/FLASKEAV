from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import enum
from sqlalchemy import JSON, Index
from sqlalchemy.ext.hybrid import hybrid_property

db = SQLAlchemy()

# ===========================================
# 1. CORE SYSTEM TABLES
# ===========================================

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # Relationships
    modules = db.relationship('Module', backref='application', lazy='dynamic')
    
    def __repr__(self):
        return f'<Application {self.code}>'

class Module(db.Model):
    __tablename__ = 'modules'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(100))
    order_index = db.Column(db.Integer, default=0)
    is_system = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # Relationships
    entity_types = db.relationship('EntityType', backref='module', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('application_id', 'code', name='unique_module_per_app'),
    )
    
    def __repr__(self):
        return f'<Module {self.code}>'

# ===========================================
# 2. ENTITY DEFINITION TABLES
# ===========================================

class DataTypeEnum(enum.Enum):
    VARCHAR = 'VARCHAR'
    TEXT = 'TEXT'
    INT = 'INT'
    BIGINT = 'BIGINT'
    DECIMAL = 'DECIMAL'
    BOOLEAN = 'BOOLEAN'
    DATE = 'DATE'
    DATETIME = 'DATETIME'
    TIMESTAMP = 'TIMESTAMP'
    JSON = 'JSON'

class EntityType(db.Model):
    __tablename__ = 'entity_types'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    table_name = db.Column(db.String(100))
    is_master = db.Column(db.Boolean, default=False)
    is_transactional = db.Column(db.Boolean, default=True)
    icon = db.Column(db.String(100))
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # Relationships
    attribute_definitions = db.relationship('AttributeDefinition', backref='entity_type', lazy='dynamic')
    form_definitions = db.relationship('FormDefinition', backref='entity_type', lazy='dynamic')
    entity_instances = db.relationship('EntityInstance', backref='entity_type', lazy='dynamic')
    workflow_states = db.relationship('WorkflowState', backref='entity_type', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('module_id', 'code', name='unique_entity_per_module'),
    )
    
    def __repr__(self):
        return f'<EntityType {self.code}>'

class AttributeDefinition(db.Model):
    __tablename__ = 'attribute_definitions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    code = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    data_type = db.Column(db.Enum(DataTypeEnum), nullable=False)
    max_length = db.Column(db.Integer)
    decimal_precision = db.Column(db.Integer)
    decimal_scale = db.Column(db.Integer)
    default_value = db.Column(db.Text)
    is_required = db.Column(db.Boolean, default=False)
    is_unique = db.Column(db.Boolean, default=False)
    is_indexed = db.Column(db.Boolean, default=False)
    validation_rules = db.Column(JSON)
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # REMOVED the problematic backref relationship that was causing conflicts
    # The relationship is now defined only in FormFieldConfiguration class
    
    __table_args__ = (
        db.UniqueConstraint('entity_type_id', 'code', name='unique_attribute_per_entity'),
    )
    
    def __repr__(self):
        return f'<AttributeDefinition {self.code}>'
# ===========================================
# 3. FORM CONFIGURATION TABLES
# ===========================================

class FormTypeEnum(enum.Enum):
    LIST = 'LIST'
    DETAIL = 'DETAIL'
    CREATE = 'CREATE'
    EDIT = 'EDIT'
    SEARCH = 'SEARCH'

class LayoutTypeEnum(enum.Enum):
    SINGLE_COLUMN = 'SINGLE_COLUMN'
    TWO_COLUMN = 'TWO_COLUMN'
    THREE_COLUMN = 'THREE_COLUMN'
    TABS = 'TABS'
    ACCORDION = 'ACCORDION'
    WIZARD = 'WIZARD'

class FieldTypeEnum(enum.Enum):
    TEXT = 'TEXT'
    TEXTAREA = 'TEXTAREA'
    NUMBER = 'NUMBER'
    DECIMAL = 'DECIMAL'
    EMAIL = 'EMAIL'
    URL = 'URL'
    PASSWORD = 'PASSWORD'
    CHECKBOX = 'CHECKBOX'
    RADIO = 'RADIO'
    SELECT = 'SELECT'
    MULTISELECT = 'MULTISELECT'
    DATE = 'DATE'
    DATETIME = 'DATETIME'
    TIME = 'TIME'
    FILE = 'FILE'
    IMAGE = 'IMAGE'
    CALCULATED = 'CALCULATED'

class FormDefinition(db.Model):
    __tablename__ = 'form_definitions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    code = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    form_type = db.Column(db.Enum(FormTypeEnum), nullable=False)
    layout_type = db.Column(db.Enum(LayoutTypeEnum), default=LayoutTypeEnum.SINGLE_COLUMN)
    records_per_page = db.Column(db.Integer, default=10)
    pages_per_load = db.Column(db.Integer, default=1)
    allow_inline_edit = db.Column(db.Boolean, default=False)
    show_attachment_count = db.Column(db.Boolean, default=False)
    mandatory_confirmation = db.Column(db.Boolean, default=False)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # Relationships
    form_field_configurations = db.relationship('FormFieldConfiguration', backref='form_definition', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('entity_type_id', 'code', 'form_type', name='unique_form_per_entity_type'),
    )
    
    def __repr__(self):
        return f'<FormDefinition {self.code}>'

class FormFieldConfiguration(db.Model):
    __tablename__ = 'form_field_configurations'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    form_definition_id = db.Column(db.Integer, db.ForeignKey('form_definitions.id'), nullable=False)
    attribute_definition_id = db.Column(db.Integer, db.ForeignKey('attribute_definitions.id'), nullable=False)
    field_label = db.Column(db.String(255))
    field_type = db.Column(db.Enum(FieldTypeEnum), nullable=False)
    placeholder_text = db.Column(db.String(255))
    help_text = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    grid_column_span = db.Column(db.Integer, default=1)
    grid_row_span = db.Column(db.Integer, default=1)
    is_visible = db.Column(db.Boolean, default=True)
    is_editable = db.Column(db.Boolean, default=True)
    is_required = db.Column(db.Boolean, default=False)
    is_searchable = db.Column(db.Boolean, default=False)
    is_sortable = db.Column(db.Boolean, default=False)
    # NEW: Simple dropdown configuration - connect directly to entity columns
    dropdown_source_entity_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'))
    dropdown_source_attribute_id = db.Column(db.Integer, db.ForeignKey('attribute_definitions.id'))
    dropdown_display_attribute_id = db.Column(db.Integer, db.ForeignKey('attribute_definitions.id'))
    show_unique_values_only = db.Column(db.Boolean, default=False)
    conditional_visibility_rules = db.Column(JSON)
    conditional_requirement_rules = db.Column(JSON)
    conditional_editability_rules = db.Column(JSON)
    validation_rules = db.Column(JSON)
    css_classes = db.Column(db.String(500))
    custom_attributes = db.Column(JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # FIXED Relationships - Explicitly specify foreign keys to avoid ambiguity
    attribute_definition = db.relationship('AttributeDefinition', 
                                         foreign_keys=[attribute_definition_id],
                                         backref='form_field_configurations')
    dropdown_source_entity = db.relationship('EntityType', 
                                            foreign_keys=[dropdown_source_entity_id])
    dropdown_source_attribute = db.relationship('AttributeDefinition', 
                                               foreign_keys=[dropdown_source_attribute_id])
    dropdown_display_attribute = db.relationship('AttributeDefinition', 
                                                foreign_keys=[dropdown_display_attribute_id])
    
    __table_args__ = (
        db.UniqueConstraint('form_definition_id', 'attribute_definition_id', name='unique_field_per_form'),
    )
    
    def __repr__(self):
        return f'<FormFieldConfiguration {self.field_label}>'
# ===========================================
# 4. DYNAMIC DATA STORAGE (EAV)
# ===========================================

class EntityInstance(db.Model):
    __tablename__ = 'entity_instances'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    instance_code = db.Column(db.String(255))
    workflow_status = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # Relationships - SIMPLIFIED (removed parent/child relationships)
    text_values = db.relationship('AttributeValueText', backref='entity_instance', lazy='dynamic', cascade='all, delete-orphan')
    numeric_values = db.relationship('AttributeValueNumeric', backref='entity_instance', lazy='dynamic', cascade='all, delete-orphan')
    datetime_values = db.relationship('AttributeValueDatetime', backref='entity_instance', lazy='dynamic', cascade='all, delete-orphan')
    boolean_values = db.relationship('AttributeValueBoolean', backref='entity_instance', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<EntityInstance {self.id}>'
    
    def get_attribute_value(self, attribute_code):
        """Get value for a specific attribute"""
        attr_def = AttributeDefinition.query.filter_by(
            entity_type_id=self.entity_type_id,
            code=attribute_code
        ).first()
        
        if not attr_def:
            return None
            
        if attr_def.data_type in [DataTypeEnum.VARCHAR, DataTypeEnum.TEXT]:
            value_obj = self.text_values.filter_by(attribute_definition_id=attr_def.id).first()
        elif attr_def.data_type in [DataTypeEnum.INT, DataTypeEnum.BIGINT, DataTypeEnum.DECIMAL]:
            value_obj = self.numeric_values.filter_by(attribute_definition_id=attr_def.id).first()
        elif attr_def.data_type in [DataTypeEnum.DATE, DataTypeEnum.DATETIME, DataTypeEnum.TIMESTAMP]:
            value_obj = self.datetime_values.filter_by(attribute_definition_id=attr_def.id).first()
        elif attr_def.data_type == DataTypeEnum.BOOLEAN:
            value_obj = self.boolean_values.filter_by(attribute_definition_id=attr_def.id).first()
        else:
            return None
            
        return value_obj.value if value_obj else None
    
    def set_attribute_value(self, attribute_code, value):
        """Set value for a specific attribute"""
        attr_def = AttributeDefinition.query.filter_by(
            entity_type_id=self.entity_type_id,
            code=attribute_code
        ).first()
        
        if not attr_def:
            return False
        
        # Handle different data types
        if attr_def.data_type in [DataTypeEnum.VARCHAR, DataTypeEnum.TEXT]:
            existing = self.text_values.filter_by(attribute_definition_id=attr_def.id).first()
            if existing:
                if value is not None:
                    existing.value = str(value)
                    existing.updated_at = datetime.utcnow()
                else:
                    db.session.delete(existing)
            elif value is not None:
                new_value = AttributeValueText(
                    entity_instance_id=self.id,
                    attribute_definition_id=attr_def.id,
                    value=str(value)
                )
                db.session.add(new_value)
                
        elif attr_def.data_type in [DataTypeEnum.INT, DataTypeEnum.BIGINT, DataTypeEnum.DECIMAL]:
            existing = self.numeric_values.filter_by(attribute_definition_id=attr_def.id).first()
            if existing:
                if value is not None:
                    existing.value = float(value)
                    existing.updated_at = datetime.utcnow()
                else:
                    db.session.delete(existing)
            elif value is not None:
                new_value = AttributeValueNumeric(
                    entity_instance_id=self.id,
                    attribute_definition_id=attr_def.id,
                    value=float(value)
                )
                db.session.add(new_value)
                
        elif attr_def.data_type in [DataTypeEnum.DATE, DataTypeEnum.DATETIME, DataTypeEnum.TIMESTAMP]:
            existing = self.datetime_values.filter_by(attribute_definition_id=attr_def.id).first()
            if existing:
                if value is not None:
                    existing.value = value
                    existing.updated_at = datetime.utcnow()
                else:
                    db.session.delete(existing)
            elif value is not None:
                new_value = AttributeValueDatetime(
                    entity_instance_id=self.id,
                    attribute_definition_id=attr_def.id,
                    value=value
                )
                db.session.add(new_value)
                
        elif attr_def.data_type == DataTypeEnum.BOOLEAN:
            existing = self.boolean_values.filter_by(attribute_definition_id=attr_def.id).first()
            if existing:
                if value is not None:
                    existing.value = bool(value)
                    existing.updated_at = datetime.utcnow()
                else:
                    db.session.delete(existing)
            elif value is not None:
                new_value = AttributeValueBoolean(
                    entity_instance_id=self.id,
                    attribute_definition_id=attr_def.id,
                    value=bool(value)
                )
                db.session.add(new_value)
        
        return True

class AttributeValueText(db.Model):
    __tablename__ = 'attribute_values_text'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_instance_id = db.Column(db.Integer, db.ForeignKey('entity_instances.id'), nullable=False)
    attribute_definition_id = db.Column(db.Integer, db.ForeignKey('attribute_definitions.id'), nullable=False)
    value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attribute_definition = db.relationship('AttributeDefinition')
    
    __table_args__ = (
        db.UniqueConstraint('entity_instance_id', 'attribute_definition_id', name='unique_instance_attribute'),
    )
    
    def __repr__(self):
        return f'<AttributeValueText {self.attribute_definition.code}={self.value}>'

class AttributeValueNumeric(db.Model):
    __tablename__ = 'attribute_values_numeric'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_instance_id = db.Column(db.Integer, db.ForeignKey('entity_instances.id'), nullable=False)
    attribute_definition_id = db.Column(db.Integer, db.ForeignKey('attribute_definitions.id'), nullable=False)
    value = db.Column(db.Numeric(20, 6))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attribute_definition = db.relationship('AttributeDefinition')
    
    __table_args__ = (
        db.UniqueConstraint('entity_instance_id', 'attribute_definition_id', name='unique_instance_attribute'),
    )
    
    def __repr__(self):
        return f'<AttributeValueNumeric {self.attribute_definition.code}={self.value}>'

class AttributeValueDatetime(db.Model):
    __tablename__ = 'attribute_values_datetime'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_instance_id = db.Column(db.Integer, db.ForeignKey('entity_instances.id'), nullable=False)
    attribute_definition_id = db.Column(db.Integer, db.ForeignKey('attribute_definitions.id'), nullable=False)
    value = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attribute_definition = db.relationship('AttributeDefinition')
    
    __table_args__ = (
        db.UniqueConstraint('entity_instance_id', 'attribute_definition_id', name='unique_instance_attribute'),
    )
    
    def __repr__(self):
        return f'<AttributeValueDatetime {self.attribute_definition.code}={self.value}>'

class AttributeValueBoolean(db.Model):
    __tablename__ = 'attribute_values_boolean'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_instance_id = db.Column(db.Integer, db.ForeignKey('entity_instances.id'), nullable=False)
    attribute_definition_id = db.Column(db.Integer, db.ForeignKey('attribute_definitions.id'), nullable=False)
    value = db.Column(db.Boolean)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    attribute_definition = db.relationship('AttributeDefinition')
    
    __table_args__ = (
        db.UniqueConstraint('entity_instance_id', 'attribute_definition_id', name='unique_instance_attribute'),
    )
    
    def __repr__(self):
        return f'<AttributeValueBoolean {self.attribute_definition.code}={self.value}>'

# ===========================================
# 5. WORKFLOW & EVENTS
# ===========================================

class WorkflowState(db.Model):
    __tablename__ = 'workflow_states'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    code = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_initial = db.Column(db.Boolean, default=False)
    is_final = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(7))  # Hex color code
    order_index = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    from_transitions = db.relationship('WorkflowTransition', foreign_keys='WorkflowTransition.from_state_id', backref='from_state', lazy='dynamic')
    to_transitions = db.relationship('WorkflowTransition', foreign_keys='WorkflowTransition.to_state_id', backref='to_state', lazy='dynamic')
    
    __table_args__ = (
        db.UniqueConstraint('entity_type_id', 'code', name='unique_state_per_entity'),
    )
    
    def __repr__(self):
        return f'<WorkflowState {self.code}>'

class WorkflowTransition(db.Model):
    __tablename__ = 'workflow_transitions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    from_state_id = db.Column(db.Integer, db.ForeignKey('workflow_states.id'), nullable=False)
    to_state_id = db.Column(db.Integer, db.ForeignKey('workflow_states.id'), nullable=False)
    action_name = db.Column(db.String(255), nullable=False)
    action_code = db.Column(db.String(100), nullable=False)
    conditions = db.Column(JSON)
    required_roles = db.Column(JSON)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<WorkflowTransition {self.action_name}>'

class EventTypeEnum(enum.Enum):
    BEFORE_CREATE = 'BEFORE_CREATE'
    AFTER_CREATE = 'AFTER_CREATE'
    BEFORE_UPDATE = 'BEFORE_UPDATE'
    AFTER_UPDATE = 'AFTER_UPDATE'
    BEFORE_DELETE = 'BEFORE_DELETE'
    AFTER_DELETE = 'AFTER_DELETE'
    ON_WORKFLOW_CHANGE = 'ON_WORKFLOW_CHANGE'

class EventConfiguration(db.Model):
    __tablename__ = 'event_configurations'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    event_type = db.Column(db.Enum(EventTypeEnum), nullable=False)
    event_name = db.Column(db.String(255), nullable=False)
    event_code = db.Column(db.String(100), nullable=False)
    conditions = db.Column(JSON)
    actions = db.Column(JSON)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity_type = db.relationship('EntityType')
    
    def __repr__(self):
        return f'<EventConfiguration {self.event_name}>'

# ===========================================
# 6. SECURITY & USER MANAGEMENT  
# ===========================================

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_system = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_roles = db.relationship('UserRole', backref='role', lazy='dynamic')
    entity_permissions = db.relationship('EntityPermission', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.code}>'

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    password = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_roles = db.relationship('UserRole', backref='user', lazy='dynamic')
    favorite_modules = db.relationship('UserFavoriteModule', backref='user', lazy='dynamic')
    
    @hybrid_property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
    
    def __repr__(self):
        return f'<User {self.username}>'

class UserRole(db.Model):
    __tablename__ = 'user_roles'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_id', name='unique_user_role'),
    )
    
    def __repr__(self):
        return f'<UserRole {self.user_id}-{self.role_id}>'

class EntityPermission(db.Model):
    __tablename__ = 'entity_permissions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'), nullable=False)
    can_read = db.Column(db.Boolean, default=False)
    can_create = db.Column(db.Boolean, default=False)
    can_update = db.Column(db.Boolean, default=False)
    can_delete = db.Column(db.Boolean, default=False)
    field_level_permissions = db.Column(JSON)
    row_level_conditions = db.Column(JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    entity_type = db.relationship('EntityType')
    
    __table_args__ = (
        db.UniqueConstraint('role_id', 'entity_type_id', name='unique_role_entity_permission'),
    )
    
    def __repr__(self):
        return f'<EntityPermission {self.role_id}-{self.entity_type_id}>'

class UserFavoriteModule(db.Model):
    __tablename__ = 'user_favorite_modules'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id'), nullable=False)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    module = db.relationship('Module')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'module_id', name='unique_user_favorite_module'),
    )
    
    def __repr__(self):
        return f'<UserFavoriteModule {self.user_id}-{self.module_id}>'

# ===========================================
# 7. APPROVAL HIERARCHY SYSTEM (SIMPLIFIED)
# ===========================================

class ApprovalType(db.Model):
    __tablename__ = 'approval_types'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<ApprovalType {self.code}>'

class UnitTypeEnum(enum.Enum):
    COMPANY = 'COMPANY'
    DIVISION = 'DIVISION'
    DEPARTMENT = 'DEPARTMENT'
    TEAM = 'TEAM'
    SECTION = 'SECTION'

class OrganizationalUnit(db.Model):
    __tablename__ = 'organizational_units'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_unit_id = db.Column(db.Integer, db.ForeignKey('organizational_units.id'))
    code = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    unit_type = db.Column(db.Enum(UnitTypeEnum), nullable=False)
    manager_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    description = db.Column(db.Text)
    level_order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(100))
    updated_by = db.Column(db.String(100))
    
    # Relationships
    parent_unit = db.relationship('OrganizationalUnit', remote_side=[id], back_populates='children')
    children = db.relationship('OrganizationalUnit', back_populates='parent_unit', overlaps="parent_unit")
    manager = db.relationship('User', foreign_keys=[manager_user_id])
    user_assignments = db.relationship('UserOrganizationalAssignment', backref='organizational_unit', lazy='dynamic')
    
    def __repr__(self):
        return f'<OrganizationalUnit {self.code}>'

class UserOrganizationalAssignment(db.Model):
    __tablename__ = 'user_organizational_assignments'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organizational_unit_id = db.Column(db.Integer, db.ForeignKey('organizational_units.id'), nullable=False)
    position_title = db.Column(db.String(255))
    is_primary = db.Column(db.Boolean, default=True)
    is_manager = db.Column(db.Boolean, default=False)
    effective_from = db.Column(db.Date, nullable=False)
    effective_to = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<UserOrganizationalAssignment {self.user_id}-{self.organizational_unit_id}>'

# ===========================================
# 8. AUDIT & LOGGING
# ===========================================

class OperationEnum(enum.Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'
    DELETE = 'DELETE'
    READ = 'READ'

class AuditLog(db.Model):
    __tablename__ = 'audit_log'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    entity_type_id = db.Column(db.Integer, db.ForeignKey('entity_types.id'))
    entity_instance_id = db.Column(db.Integer, db.ForeignKey('entity_instances.id'))
    operation = db.Column(db.Enum(OperationEnum), nullable=False)
    old_values = db.Column(JSON)
    new_values = db.Column(JSON)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    entity_type = db.relationship('EntityType')
    entity_instance = db.relationship('EntityInstance')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<AuditLog {self.operation.value}>'

class SystemParameterDataTypeEnum(enum.Enum):
    STRING = 'STRING'
    INTEGER = 'INTEGER'
    DECIMAL = 'DECIMAL'
    BOOLEAN = 'BOOLEAN'
    JSON = 'JSON'

class SystemParameter(db.Model):
    __tablename__ = 'system_parameters'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category = db.Column(db.String(100), nullable=False)
    param_key = db.Column(db.String(255), nullable=False)
    param_value = db.Column(db.Text)
    data_type = db.Column(db.Enum(SystemParameterDataTypeEnum), default=SystemParameterDataTypeEnum.STRING)
    description = db.Column(db.Text)
    is_encrypted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('category', 'param_key', name='unique_category_key'),
    )
    
    def __repr__(self):
        return f'<SystemParameter {self.category}.{self.param_key}>'

# ===========================================
# 9. INDEXES FOR PERFORMANCE
# ===========================================

# Entity Instances indexes
Index('idx_entity_instances_type_status', EntityInstance.entity_type_id, EntityInstance.workflow_status)
Index('idx_entity_instances_created', EntityInstance.created_at)
Index('idx_entity_type_active', EntityInstance.entity_type_id, EntityInstance.is_active)

# Attribute Values indexes
Index('idx_attr_values_text_value', AttributeValueText.value)
Index('idx_attr_values_numeric_value', AttributeValueNumeric.value)
Index('idx_attr_values_datetime_value', AttributeValueDatetime.value)

# Form Configurations indexes
Index('idx_form_fields_form_order', FormFieldConfiguration.form_definition_id, FormFieldConfiguration.order_index)
Index('idx_form_definitions_entity', FormDefinition.entity_type_id, FormDefinition.form_type)

# Audit Log indexes
Index('idx_entity_instance_operation', AuditLog.entity_instance_id, AuditLog.operation)
Index('idx_audit_created_at', AuditLog.created_at)

# ===========================================
# 10. HELPER FUNCTIONS
# ===========================================

def get_user_permissions(user_id, entity_type_id):
    """
    Get detailed permissions for a user on an entity type
    Returns dict with can_read, can_create, can_update, can_delete
    This is used by templates to show/hide UI elements
    """
    user = User.query.get(user_id)
    if not user:
        return {
            'can_read': False,
            'can_create': False,
            'can_update': False,
            'can_delete': False
        }
    
    # Get all role IDs for this user
    user_role_ids = [ur.role_id for ur in user.user_roles]
    
    # Get all permissions for these roles and this entity type
    permissions = EntityPermission.query.filter(
        EntityPermission.role_id.in_(user_role_ids),
        EntityPermission.entity_type_id == entity_type_id
    ).all()
    
    # Aggregate permissions (if user has multiple roles, grant if ANY role has permission)
    result = {
        'can_read': False,
        'can_create': False,
        'can_update': False,
        'can_delete': False
    }
    
    for perm in permissions:
        if perm.can_read:
            result['can_read'] = True
        if perm.can_create:
            result['can_create'] = True
        if perm.can_update:
            result['can_update'] = True
        if perm.can_delete:
            result['can_delete'] = True
    
    return result

def can_access_module(user_id, module_id):
    """
    Check if user can access any entity in a module
    Returns True if user has read permission for at least one entity in the module
    """
    user = User.query.get(user_id)
    if not user:
        return False
    
    user_role_ids = [ur.role_id for ur in user.user_roles]
    
    # Get all entity types in this module
    entity_types = EntityType.query.filter_by(module_id=module_id, is_active=True).all()
    entity_type_ids = [et.id for et in entity_types]
    
    if not entity_type_ids:
        return False
    
    # Check if user has read permission for any entity in the module
    permissions = EntityPermission.query.filter(
        EntityPermission.role_id.in_(user_role_ids),
        EntityPermission.entity_type_id.in_(entity_type_ids),
        EntityPermission.can_read == True
    ).first()
    
    return permissions is not None

def get_accessible_entity_types_for_module(user_id, module_id):
    """
    Get list of entity types in a module that the user can read
    Returns list of EntityType objects
    """
    user = User.query.get(user_id)
    if not user:
        return []
    
    user_role_ids = [ur.role_id for ur in user.user_roles]
    
    # Get all entity types in this module
    entity_types = EntityType.query.filter_by(
        module_id=module_id, 
        is_active=True
    ).order_by(EntityType.order_index).all()
    
    # Get permissions for these entity types
    entity_type_ids = [et.id for et in entity_types]
    permissions = EntityPermission.query.filter(
        EntityPermission.role_id.in_(user_role_ids),
        EntityPermission.entity_type_id.in_(entity_type_ids),
        EntityPermission.can_read == True
    ).all()
    
    # Create set of accessible entity type IDs
    accessible_ids = {perm.entity_type_id for perm in permissions}
    
    # Filter entity types to only those accessible
    return [et for et in entity_types if et.id in accessible_ids]

def get_dropdown_options(entity_type_id, source_attribute_code, display_attribute_code=None, unique_only=False):
    """Get dropdown options from entity instances"""
    try:
        entity_type = EntityType.query.get(entity_type_id)
        if not entity_type:
            return []
        
        # Get source attribute definition
        source_attr = AttributeDefinition.query.filter_by(
            entity_type_id=entity_type_id,
            code=source_attribute_code,
            is_active=True
        ).first()
        
        if not source_attr:
            return []
        
        # Get display attribute definition (use source if not specified)
        display_attr = source_attr
        if display_attribute_code and display_attribute_code != source_attribute_code:
            display_attr = AttributeDefinition.query.filter_by(
                entity_type_id=entity_type_id,
                code=display_attribute_code,
                is_active=True
            ).first()
            if not display_attr:
                display_attr = source_attr
        
        # Get all active instances
        instances = EntityInstance.query.filter_by(
            entity_type_id=entity_type_id,
            is_active=True
        ).all()
        
        options = []
        seen_values = set()
        
        for instance in instances:
            source_value = instance.get_attribute_value(source_attribute_code)
            display_value = instance.get_attribute_value(display_attr.code)
            
            if source_value is not None:
                # For unique_only, skip if we've seen this value before
                if unique_only and source_value in seen_values:
                    continue
                    
                seen_values.add(source_value)
                options.append({
                    'value': source_value,
                    'label': display_value or source_value,
                    'instance_id': instance.id
                })
        
        # Sort options by label
        options.sort(key=lambda x: str(x['label']))
        return options
        
    except Exception as e:
        print(f"Error getting dropdown options: {e}")
        return []



def get_entity_instances_with_attributes(entity_type_id, page=1, per_page=10):
    """Get entity instances with their attribute values"""
    entity_type = EntityType.query.get(entity_type_id)
    if not entity_type:
        return None, None
    
    attributes = AttributeDefinition.query.filter_by(
        entity_type_id=entity_type_id,
        is_active=True
    ).order_by(AttributeDefinition.order_index).all()
    
    instances = EntityInstance.query.filter_by(
        entity_type_id=entity_type_id,
        is_active=True
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    result = []
    for instance in instances.items:
        instance_data = {
            'id': instance.id,
            'instance_code': instance.instance_code,
            'workflow_status': instance.workflow_status,
            'created_at': instance.created_at,
            'updated_at': instance.updated_at,
            'attributes': {}
        }
        
        for attr in attributes:
            value = instance.get_attribute_value(attr.code)
            instance_data['attributes'][attr.code] = {
                'definition': attr,
                'value': value
            }
        
        result.append(instance_data)
    
    return result, instances

def create_entity_instance_with_attributes(entity_type_id, attribute_values, created_by=None):
    """Create a new entity instance with attribute values"""
    try:
        instance = EntityInstance(
            entity_type_id=entity_type_id,
            created_by=created_by or 'system'
        )
        db.session.add(instance)
        db.session.flush()
        
        for attr_code, value in attribute_values.items():
            if value is not None:
                instance.set_attribute_value(attr_code, value)
        
        db.session.commit()
        return instance
        
    except Exception as e:
        db.session.rollback()
        raise e

def update_entity_instance_attributes(instance_id, attribute_values, updated_by=None):
    """Update attribute values for an entity instance"""
    try:
        instance = EntityInstance.query.get(instance_id)
        if not instance:
            return None
        
        instance.updated_by = updated_by or 'system'
        instance.updated_at = datetime.utcnow()
        
        for attr_code, value in attribute_values.items():
            instance.set_attribute_value(attr_code, value)
        
        db.session.commit()
        return instance
        
    except Exception as e:
        db.session.rollback()
        raise e

def check_user_permissions(user_id, entity_type_id, operation):
    """Check if user has permission for operation on entity type"""
    user = User.query.get(user_id)
    if not user:
        return False
    
    user_roles = [ur.role_id for ur in user.user_roles]
    
    permissions = EntityPermission.query.filter(
        EntityPermission.role_id.in_(user_roles),
        EntityPermission.entity_type_id == entity_type_id
    ).all()
    
    for permission in permissions:
        if operation == 'READ' and permission.can_read:
            return True
        elif operation == 'CREATE' and permission.can_create:
            return True
        elif operation == 'UPDATE' and permission.can_update:
            return True
        elif operation == 'DELETE' and permission.can_delete:
            return True
    
    return False

def log_audit_entry(entity_type_id, entity_instance_id, operation, old_values=None, new_values=None, user_id=None, ip_address=None, user_agent=None):
    """Create an audit log entry"""
    try:
        audit_entry = AuditLog(
            entity_type_id=entity_type_id,
            entity_instance_id=entity_instance_id,
            operation=operation,
            old_values=old_values,
            new_values=new_values,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(audit_entry)
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        print(f"Error creating audit log: {e}")

def get_workflow_next_states(current_state_id, user_roles=None):
    """Get possible next workflow states for current state"""
    transitions = WorkflowTransition.query.filter_by(
        from_state_id=current_state_id,
        is_active=True
    ).all()
    
    if user_roles:
        valid_transitions = []
        for transition in transitions:
            if not transition.required_roles:
                valid_transitions.append(transition)
            else:
                required_roles = transition.required_roles
                if any(role in user_roles for role in required_roles):
                    valid_transitions.append(transition)
        return valid_transitions
    
    return transitions

def initialize_database():
    """Initialize database with tables and sample data"""
    try:
        db.create_all()
        print("Database tables created successfully!")
        
    except Exception as e:
        print(f"Error initializing database: {e}")

# Export all models for easy importing
__all__ = [
    'db',
    # Core System
    'Application', 'Module',
    # Entity Definition
    'EntityType', 'AttributeDefinition', 'DataTypeEnum',
    # Form Configuration
    'FormDefinition', 'FormFieldConfiguration', 'FormTypeEnum', 'LayoutTypeEnum', 'FieldTypeEnum',
    # EAV Data Storage
    'EntityInstance', 'AttributeValueText', 'AttributeValueNumeric', 'AttributeValueDatetime', 'AttributeValueBoolean',
    # Workflow
    'WorkflowState', 'WorkflowTransition', 'EventConfiguration', 'EventTypeEnum',
    # Approval System (Simplified)
    'ApprovalType', 'OrganizationalUnit', 'UserOrganizationalAssignment', 'UnitTypeEnum',
    # Security
    'User', 'Role', 'UserRole', 'EntityPermission', 'UserFavoriteModule',
    # Audit & System
    'AuditLog', 'SystemParameter', 'OperationEnum', 'SystemParameterDataTypeEnum',
    # Helper Functions
    'get_entity_instances_with_attributes',
    'create_entity_instance_with_attributes', 'update_entity_instance_attributes',
    'check_user_permissions', 'log_audit_entry', 'get_workflow_next_states', 
    'initialize_database', 'get_dropdown_options','get_user_permissions',
    'can_access_module', 
    'get_accessible_entity_types_for_module'
]