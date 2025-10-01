from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json

# Import models and admin views
from models import *

# Import custom admin
from custom_admin import admin_bp, AdminConfig, AdminUtils
from entity_designer import entity_designer_bp
from access_control import access_control_bp

# Create Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///port_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ===========================================
# CSRF TOKEN HELPER
# ===========================================

from flask_wtf.csrf import generate_csrf

@app.context_processor
def inject_csrf_token():
    """Make CSRF token available in all templates"""
    return dict(csrf_token=generate_csrf)

@app.context_processor
def inject_permissions():
    """Inject permission checker into all templates"""
    def has_permission(entity_type_id, permission_type):
        if not current_user.is_authenticated:
            return False
        perms = get_user_permissions(current_user.id, entity_type_id)
        return perms.get(f'can_{permission_type.lower()}', False)
    
    def get_permissions(entity_type_id):
        if not current_user.is_authenticated:
            return {'can_read': False, 'can_create': False, 'can_update': False, 'can_delete': False}
        return get_user_permissions(current_user.id, entity_type_id)
    
    return {
        'has_permission': has_permission,
        'get_permissions': get_permissions
    }

# ===========================================
# CUSTOM ADMIN INTEGRATION
# ===========================================

# Register the custom admin blueprint
app.register_blueprint(admin_bp)
app.register_blueprint(entity_designer_bp)
app.register_blueprint(access_control_bp)
# Add template filters for admin
@app.template_filter('get_display_value')
def get_display_value_filter(obj, field_name):
    """Template filter to get display value for any field"""
    return AdminUtils.get_display_value(obj, field_name)

# Add context processor for admin navigation
@app.context_processor  
def inject_admin_navigation():
    """Inject admin navigation for admin routes only"""
    if request.endpoint and request.endpoint.startswith('custom_admin.'):
        return {
            'navigation': AdminConfig.get_navigation_structure(),
            'get_display_value': AdminUtils.get_display_value
        }
    return {}

# ===========================================
# INITIALIZATION FUNCTIONS
# ===========================================

def create_admin_user():
    """Create admin user if it doesn't exist"""
    try:
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            # Create admin role first
            admin_role = Role.query.filter_by(code='ADMIN').first()
            if not admin_role:
                admin_role = Role(
                    code='ADMIN',
                    name='Administrator',
                    description='System administrator with full access',
                    is_system=True,
                    is_active=True
                )
                db.session.add(admin_role)
                db.session.flush()
            
            # Create admin user
            admin_user = User(
                username='admin',
                email='admin@portmgmt.com',
                first_name='System',
                last_name='Administrator',
                password=generate_password_hash('admin123'),
                is_active=True
            )
            db.session.add(admin_user)
            db.session.flush()
            
            # Assign admin role
            user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
            db.session.add(user_role)
            
            db.session.commit()
            print("Admin user created: username='admin', password='admin123'")
        else:
            print("Admin user already exists")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error creating admin user: {e}")
        raise e

def initialize_app():
    """Initialize the application"""
    try:
        # Create database tables
        db.create_all()
        
        # Create admin user
        create_admin_user()
        
        # Create sample data if needed

            
        print("Application initialized successfully!")
        print("Access main app at: http://localhost:5000/")
        print("Access admin panel at: http://localhost:5000/custom-admin/")
            
    except Exception as e:
        print(f"Error during initialization: {e}")

# ===========================================
# AUTHENTICATION ROUTES
# ===========================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

# ===========================================
# MAIN DASHBOARD ROUTES
# ===========================================

@app.route('/')
@login_required
def dashboard():
    """Main dashboard with SAP-like interface"""
    # Get user's favorite modules
    favorite_modules_query = db.session.query(UserFavoriteModule, Module).join(
        Module, UserFavoriteModule.module_id == Module.id
    ).filter(
        UserFavoriteModule.user_id == current_user.id
    ).order_by(UserFavoriteModule.order_index).all()
    
    # Extract just the modules from the query result
    favorite_modules = [fm[1] for fm in favorite_modules_query]
    
    # Get all applications and their modules
    applications = Application.query.filter_by(is_active=True).order_by(Application.order_index).all()
    
    # Get recent activities (placeholder for now)
    recent_activities = []
    
    return render_template('dashboard/main.html', 
                         favorite_modules=favorite_modules,
                         applications=applications,
                         recent_activities=recent_activities)

@app.route('/module/<int:module_id>')
@login_required
def module_view(module_id):
    """Display module with its entity types - filtered by permissions"""
    module = Module.query.get_or_404(module_id)
    
    # Check if user can access this module
    if not can_access_module(current_user.id, module_id):
        flash('You do not have permission to access this module', 'error')
        return redirect(url_for('dashboard'))
    
    # Get entity types user has read access to
    accessible_entities = get_accessible_entity_types_for_module(current_user.id, module_id)
    
    # Get user's favorite modules
    favorite_modules_query = db.session.query(Module).join(UserFavoriteModule).filter(
        UserFavoriteModule.user_id == current_user.id
    ).all()
    
    return render_template('modules/module_view.html', 
                         module=module, 
                         entity_types=accessible_entities,
                         favorite_modules=favorite_modules_query)


# ===========================================
# ENTITY MANAGEMENT ROUTES
# ===========================================

def process_form_data(form_fields, request_form):
    """Process form data with proper type conversion and validation"""
    attribute_values = {}
    
    for field in form_fields:
        field_name = f"attr_{field.attribute_definition.code}"
        value = request_form.get(field_name)
        
        # Skip processing if field is not visible or editable
        if not field.is_visible:
            continue
            
        # Handle empty values
        if not value or value.strip() == '':
            # Only set None if field is not required
            if not (field.is_required or field.attribute_definition.is_required):
                attribute_values[field.attribute_definition.code] = None
            continue
        
        # Process based on data type
        try:
            if field.attribute_definition.data_type in [DataTypeEnum.INT, DataTypeEnum.BIGINT]:
                attribute_values[field.attribute_definition.code] = int(value)
            elif field.attribute_definition.data_type == DataTypeEnum.DECIMAL:
                attribute_values[field.attribute_definition.code] = float(value)
            elif field.attribute_definition.data_type == DataTypeEnum.BOOLEAN:
                attribute_values[field.attribute_definition.code] = value.lower() in ['true', '1', 'yes', 'on']
            elif field.attribute_definition.data_type in [DataTypeEnum.DATE, DataTypeEnum.DATETIME]:
                if value:
                    # Handle both date and datetime formats
                    if 'T' in value:
                        attribute_values[field.attribute_definition.code] = datetime.strptime(value, '%Y-%m-%dT%H:%M')
                    else:
                        attribute_values[field.attribute_definition.code] = datetime.strptime(value, '%Y-%m-%d')
            else:
                # VARCHAR, TEXT, and other string types
                attribute_values[field.attribute_definition.code] = value.strip()
                
        except (ValueError, TypeError) as e:
            print(f"Error converting field {field.attribute_definition.code} with value '{value}': {e}")
            # For conversion errors, either skip or set to None
            if not (field.is_required or field.attribute_definition.is_required):
                attribute_values[field.attribute_definition.code] = None
            else:
                raise ValueError(f"Invalid value for {field.attribute_definition.name}: {value}")
    
    return attribute_values

@app.route('/entity/<int:entity_type_id>')
@login_required
def entity_list(entity_type_id):
    """Display list of entity instances"""
    entity_type = EntityType.query.get_or_404(entity_type_id)
    
    # Check read permission
    if not check_user_permissions(current_user.id, entity_type_id, 'READ'):
        flash('You do not have permission to view this entity', 'error')
        return redirect(url_for('dashboard'))
    
    list_form = FormDefinition.query.filter_by(
        entity_type_id=entity_type_id,
        form_type=FormTypeEnum.LIST,
        is_active=True
    ).first()
    
    if not list_form:
        flash('No list form configured for this entity type', 'error')
        return redirect(url_for('module_view', module_id=entity_type.module_id))
    
    form_fields = FormFieldConfiguration.query.filter_by(
        form_definition_id=list_form.id,
        is_visible=True
    ).join(
    AttributeDefinition,
    FormFieldConfiguration.attribute_definition_id == AttributeDefinition.id
    ).order_by(FormFieldConfiguration.order_index).all()
    
    page = request.args.get('page', 1, type=int)
    per_page = list_form.records_per_page or 10
    
    instances_data, pagination = get_entity_instances_with_attributes(
        entity_type_id, page=page, per_page=per_page
    )
    
    # Get permissions for template
    permissions = get_user_permissions(current_user.id, entity_type_id)
    
    return render_template('entities/entity_list.html',
                         entity_type=entity_type,
                         list_form=list_form,
                         form_fields=form_fields,
                         instances_data=instances_data,
                         pagination=pagination,
                         permissions=permissions)

@app.route('/entity/<int:entity_type_id>/create', methods=['GET', 'POST'])
@login_required
def entity_create(entity_type_id):
    """Create new entity instance"""
    entity_type = EntityType.query.get_or_404(entity_type_id)
    
    # Check create permission
    if not check_user_permissions(current_user.id, entity_type_id, 'CREATE'):
        flash('You do not have permission to create records in this entity', 'error')
        return redirect(url_for('entity_list', entity_type_id=entity_type_id))
    
    create_form = FormDefinition.query.filter_by(
        entity_type_id=entity_type_id,
        form_type=FormTypeEnum.CREATE,
        is_active=True
    ).first()
    
    if not create_form:
        flash('No create form configured for this entity type', 'error')
        return redirect(url_for('entity_list', entity_type_id=entity_type_id))
    
    form_fields = FormFieldConfiguration.query.filter_by(
        form_definition_id=create_form.id,
        is_visible=True
    ).join(
    AttributeDefinition,
    FormFieldConfiguration.attribute_definition_id == AttributeDefinition.id    
    ).order_by(FormFieldConfiguration.order_index).all()
    
    if request.method == 'POST':
        try:
            attribute_values = process_form_data(form_fields, request.form)
            
            instance = create_entity_instance_with_attributes(
                entity_type_id=entity_type_id,
                attribute_values=attribute_values,
                created_by=current_user.username
            )
            
            # Log audit entry
            log_audit_entry(
                entity_type_id=entity_type_id,
                entity_instance_id=instance.id,
                operation=OperationEnum.CREATE,
                new_values=attribute_values,
                user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash(f'{entity_type.name} created successfully', 'success')
            return redirect(url_for('entity_detail', entity_type_id=entity_type_id, instance_id=instance.id))
            
        except Exception as e:
            flash(f'Error creating {entity_type.name}: {str(e)}', 'error')
            print(f"Entity creation error: {e}")
    
    dropdown_data = {}
    for field in form_fields:
        if field.field_type in [FieldTypeEnum.SELECT, FieldTypeEnum.MULTISELECT]:
            if field.dropdown_source_entity_id and field.dropdown_source_attribute_id:
                display_attr_code = field.dropdown_display_attribute.code if field.dropdown_display_attribute else field.dropdown_source_attribute.code
                options = get_dropdown_options(
                    entity_type_id=field.dropdown_source_entity_id,
                    source_attribute_code=field.dropdown_source_attribute.code,
                    display_attribute_code=display_attr_code,
                    unique_only=field.show_unique_values_only
                )
                dropdown_data[field.attribute_definition.code] = options
    
    permissions = get_user_permissions(current_user.id, entity_type_id)
    
    return render_template('entities/entity_form.html',
                         entity_type=entity_type,
                         form_definition=create_form,
                         form_fields=form_fields,
                         lookup_data=dropdown_data,
                         instance=None,
                         form_action='create',
                         permissions=permissions)

@app.route('/entity/<int:entity_type_id>/<int:instance_id>/edit', methods=['GET', 'POST'])
@login_required
def entity_edit(entity_type_id, instance_id):
    """Edit entity instance"""
    entity_type = EntityType.query.get_or_404(entity_type_id)
    instance = EntityInstance.query.get_or_404(instance_id)
    
    # Check update permission
    if not check_user_permissions(current_user.id, entity_type_id, 'UPDATE'):
        flash('You do not have permission to edit records in this entity', 'error')
        return redirect(url_for('entity_detail', entity_type_id=entity_type_id, instance_id=instance_id))
    
    edit_form = FormDefinition.query.filter_by(
        entity_type_id=entity_type_id,
        form_type=FormTypeEnum.EDIT,
        is_active=True
    ).first()
    
    if not edit_form:
        flash('No edit form configured for this entity type', 'error')
        return redirect(url_for('entity_detail', entity_type_id=entity_type_id, instance_id=instance_id))
    
    form_fields = FormFieldConfiguration.query.filter_by(
        form_definition_id=edit_form.id,
        is_visible=True
    ).join(
    AttributeDefinition,
    FormFieldConfiguration.attribute_definition_id == AttributeDefinition.id
    ).order_by(FormFieldConfiguration.order_index).all()
    
    if request.method == 'POST':
        try:
            # Get old values for audit
            old_values = {}
            for field in form_fields:
                old_values[field.attribute_definition.code] = instance.get_attribute_value(field.attribute_definition.code)
            
            attribute_values = process_form_data(form_fields, request.form)
            
            update_entity_instance_attributes(
                instance_id=instance.id,
                attribute_values=attribute_values,
                updated_by=current_user.username
            )
            
            # Log audit entry
            log_audit_entry(
                entity_type_id=entity_type_id,
                entity_instance_id=instance.id,
                operation=OperationEnum.UPDATE,
                old_values=old_values,
                new_values=attribute_values,
                user_id=current_user.id,
                ip_address=request.remote_addr,
                user_agent=request.user_agent.string
            )
            
            flash(f'{entity_type.name} updated successfully', 'success')
            return redirect(url_for('entity_detail', entity_type_id=entity_type_id, instance_id=instance.id))
            
        except Exception as e:
            flash(f'Error updating {entity_type.name}: {str(e)}', 'error')
            print(f"Entity update error: {e}")
    
    current_values = {}
    for field in form_fields:
        value = instance.get_attribute_value(field.attribute_definition.code)
        current_values[field.attribute_definition.code] = value
    
    dropdown_data = {}
    for field in form_fields:
        if field.field_type in [FieldTypeEnum.SELECT, FieldTypeEnum.MULTISELECT]:
            if field.dropdown_source_entity_id and field.dropdown_source_attribute_id:
                display_attr_code = field.dropdown_display_attribute.code if field.dropdown_display_attribute else field.dropdown_source_attribute.code
                options = get_dropdown_options(
                    entity_type_id=field.dropdown_source_entity_id,
                    source_attribute_code=field.dropdown_source_attribute.code,
                    display_attribute_code=display_attr_code,
                    unique_only=field.show_unique_values_only
                )
                dropdown_data[field.attribute_definition.code] = options
    
    permissions = get_user_permissions(current_user.id, entity_type_id)
    
    return render_template('entities/entity_form.html',
                         entity_type=entity_type,
                         form_definition=edit_form,
                         form_fields=form_fields,
                         lookup_data=dropdown_data,
                         instance=instance,
                         current_values=current_values,
                         form_action='edit',
                         permissions=permissions)

@app.route('/entity/<int:entity_type_id>/<int:instance_id>')
@login_required
def entity_detail(entity_type_id, instance_id):
    """Display entity instance detail"""
    entity_type = EntityType.query.get_or_404(entity_type_id)
    instance = EntityInstance.query.get_or_404(instance_id)
    
    # Check read permission
    if not check_user_permissions(current_user.id, entity_type_id, 'READ'):
        flash('You do not have permission to view this entity', 'error')
        return redirect(url_for('dashboard'))
    
    detail_form = FormDefinition.query.filter_by(
        entity_type_id=entity_type_id,
        form_type=FormTypeEnum.DETAIL,
        is_active=True
    ).first()
    
    if not detail_form:
        flash('No detail form configured for this entity type', 'error')
        return redirect(url_for('entity_list', entity_type_id=entity_type_id))
    
    form_fields = FormFieldConfiguration.query.filter_by(
        form_definition_id=detail_form.id,
        is_visible=True
    ).join(
    AttributeDefinition,
    FormFieldConfiguration.attribute_definition_id == AttributeDefinition.id
    ).order_by(FormFieldConfiguration.order_index).all()    
    
    instance_data = {
        'id': instance.id,
        'instance_code': instance.instance_code,
        'workflow_status': instance.workflow_status,
        'created_at': instance.created_at,
        'updated_at': instance.updated_at,
        'attributes': {}
    }
    
    for field in form_fields:
        value = instance.get_attribute_value(field.attribute_definition.code)
        instance_data['attributes'][field.attribute_definition.code] = {
            'definition': field.attribute_definition,
            'value': value
        }
    
    permissions = get_user_permissions(current_user.id, entity_type_id)
    
    return render_template('entities/entity_detail.html',
                         entity_type=entity_type,
                         instance=instance,
                         instance_data=instance_data,
                         form_fields=form_fields,
                         permissions=permissions)

@app.route('/entity/<int:entity_type_id>/<int:instance_id>/delete', methods=['POST'])
@login_required
def entity_delete(entity_type_id, instance_id):
    """Delete entity instance (soft delete)"""
    # Check delete permission
    if not check_user_permissions(current_user.id, entity_type_id, 'DELETE'):
        return jsonify({'success': False, 'error': 'You do not have permission to delete this record'}), 403
    
    try:
        entity_type = EntityType.query.get_or_404(entity_type_id)
        instance = EntityInstance.query.get_or_404(instance_id)
        
        if instance.entity_type_id != entity_type_id:
            return jsonify({'success': False, 'error': 'Invalid instance'}), 400
        
        # Get values for audit log
        old_values = {'instance_code': instance.instance_code, 'workflow_status': instance.workflow_status}
        
        # Log audit entry before deletion
        log_audit_entry(
            entity_type_id=entity_type_id,
            entity_instance_id=instance_id,
            operation=OperationEnum.DELETE,
            old_values=old_values,
            user_id=current_user.id,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        
        # Soft delete - set is_active to False
        instance.is_active = False
        instance.updated_by = current_user.username
        instance.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Record deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ===========================================
# FAVORITES MANAGEMENT
# ===========================================

@app.route('/favorites/toggle/<int:module_id>', methods=['POST'])
@login_required
def toggle_favorite(module_id):
    """Toggle module as favorite for current user"""
    try:
        # Validate CSRF token manually
        csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
        if not csrf_token:
            return jsonify({'success': False, 'error': 'CSRF token missing'}), 400
        
        # Check if module exists
        module = Module.query.get(module_id)
        if not module:
            return jsonify({'success': False, 'error': 'Module not found'}), 404
        
        existing = UserFavoriteModule.query.filter_by(
            user_id=current_user.id,
            module_id=module_id
        ).first()
        
        if existing:
            db.session.delete(existing)
            action = 'removed'
        else:
            # Get the next order index
            max_order = db.session.query(db.func.max(UserFavoriteModule.order_index)).filter_by(
                user_id=current_user.id
            ).scalar() or 0
            
            favorite = UserFavoriteModule(
                user_id=current_user.id,
                module_id=module_id,
                order_index=max_order + 1
            )
            db.session.add(favorite)
            action = 'added'
        
        db.session.commit()
        return jsonify({'success': True, 'action': action}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"Error toggling favorite: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/favorites/reorder', methods=['POST'])
@login_required
def reorder_favorites():
    """Reorder favorite modules"""
    try:
        # Validate CSRF token manually
        csrf_token = request.headers.get('X-CSRFToken') or request.json.get('csrf_token') if request.json else None
        if not csrf_token:
            return jsonify({'success': False, 'error': 'CSRF token missing'}), 400
            
        data = request.get_json()
        if not data or 'module_ids' not in data:
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
            
        module_ids = data.get('module_ids', [])
        
        for index, module_id in enumerate(module_ids):
            favorite = UserFavoriteModule.query.filter_by(
                user_id=current_user.id,
                module_id=module_id
            ).first()
            if favorite:
                favorite.order_index = index + 1
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        print(f"Error reordering favorites: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===========================================
# API ENDPOINTS
# ===========================================

@app.route('/api/dropdown/<int:entity_type_id>/<attribute_code>')
@login_required
def api_dropdown_options(entity_type_id, attribute_code):
    """Get dropdown options from entity data"""
    display_attribute_code = request.args.get('display_attribute')
    unique_only = request.args.get('unique_only', 'false').lower() == 'true'
    
    options = get_dropdown_options(
        entity_type_id=entity_type_id,
        source_attribute_code=attribute_code,
        display_attribute_code=display_attribute_code,
        unique_only=unique_only
    )
    
    return jsonify(options)

@app.route('/custom-admin/api/entity/<int:entity_id>/attributes')
@login_required
def api_entity_attributes(entity_id):
    """Get attributes for an entity type"""
    attributes = AttributeDefinition.query.filter_by(
        entity_type_id=entity_id,
        is_active=True
    ).order_by(AttributeDefinition.order_index).all()
    
    return jsonify([{
        'id': attr.id,
        'code': attr.code,
        'name': attr.name,
        'data_type': attr.data_type.value
    } for attr in attributes])

@app.route('/api/entity/<int:entity_type_id>/search')
@login_required
def api_entity_search(entity_type_id):
    """Search entity instances"""
    search_term = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Basic search implementation (can be enhanced)
    instances = EntityInstance.query.filter_by(
        entity_type_id=entity_type_id,
        is_active=True
    )
    
    if search_term:
        instances = instances.filter(
            EntityInstance.instance_code.ilike(f'%{search_term}%')
        )
    
    pagination = instances.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'instances': [{
            'id': inst.id,
            'instance_code': inst.instance_code,
            'workflow_status': inst.workflow_status,
            'created_at': inst.created_at.isoformat() if inst.created_at else None
        } for inst in pagination.items],
        'pagination': {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

# ===========================================
# ERROR HANDLERS
# ===========================================

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# ===========================================
# TEMPLATE HELPERS AND FILTERS
# ===========================================

@app.template_filter('format_datetime')
def format_datetime(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return ''
    return value.strftime(format)

@app.template_filter('format_date')
def format_date(value, format='%Y-%m-%d'):
    if value is None:
        return ''
    return value.strftime(format)

@app.template_filter('format_currency')
def format_currency(value):
    if value is None:
        return ''
    return f"${value:,.2f}"

# Add hasattr as a global function for templates
@app.template_global()
def hasattr_helper(obj, attr_name):
    """Template helper to check if an object has an attribute"""
    try:
        return hasattr(obj, attr_name)
    except:
        return False

# Add getattr as a global function for templates
@app.template_global()
def getattr_helper(obj, attr_name, default=None):
    """Template helper to safely get an attribute"""
    try:
        return getattr(obj, attr_name, default)
    except:
        return default

# Make Python's hasattr and getattr available in templates
@app.context_processor
def inject_python_builtins():
    """Make Python builtins available in templates"""
    return {
        'hasattr': hasattr,
        'getattr': getattr,
        'len': len,
        'str': str,
        'int': int,
        'float': float,
        'bool': bool
    }

# ===========================================
# ADMIN EXPORT ROUTE
# ===========================================

@app.route('/admin/export/<model_name>')
@login_required
def export_model(model_name):
    """Export model data to CSV"""
    import csv
    from io import StringIO
    from flask import make_response
    
    config = AdminConfig.get_model_config(model_name)
    if not config:
        flash('Model not found', 'error')
        return redirect(url_for('custom_admin.dashboard'))
    
    model = config['model']
    objects = model.query.all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write headers
    headers = config.get('list_display', ['id'])
    writer.writerow(headers)
    
    # Write data
    for obj in objects:
        row = []
        for field in headers:
            value = AdminUtils.get_display_value(obj, field)
            row.append(value)
        writer.writerow(row)
    
    # Create response
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename={model_name}_export.csv'
    
    return response

# ===========================================
# APPLICATION STARTUP
# ===========================================

# Initialize the app when it starts
with app.app_context():
    initialize_app()

if __name__ == '__main__':
    print("="*60)
    print("PORT MANAGEMENT SYSTEM STARTED")
    print("="*60)
    print("Main Application: http://localhost:5000/")
    print("Admin Panel: http://localhost:5000/custom-admin/")
    print("Login with: admin / admin123")
    print("="*60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)