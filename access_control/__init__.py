"""
Access Control Module for Port Management System
Handles user permissions and role assignments
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import *

access_control_bp = Blueprint('access_control', __name__, 
                             url_prefix='/access-control',
                             template_folder='templates')

@access_control_bp.route('/')
@login_required
def index():
    """Main access control interface"""
    roles = Role.query.filter_by(is_active=True).order_by(Role.name).all()
    entity_types = EntityType.query.filter_by(is_active=True).order_by(EntityType.name).all()
    users = User.query.filter_by(is_active=True).order_by(User.username).all()
    
    # Include module information in entity types
    entity_data = []
    for entity in entity_types:
        entity_data.append({
            'id': entity.id,
            'name': entity.name,
            'module': {
                'name': entity.module.name,
                'application': entity.module.application.name
            }
        })
    
    # Count total permissions
    total_permissions = EntityPermission.query.count()
    
    return render_template('access_control/index.html',
                         roles=roles,
                         entity_types=entity_data,
                         users=users,
                         total_permissions=total_permissions)

@access_control_bp.route('/role/<int:role_id>/permissions')
@login_required
def get_role_permissions(role_id):
    """Get all permissions for a role"""
    permissions = EntityPermission.query.filter_by(role_id=role_id).all()
    
    result = []
    for perm in permissions:
        result.append({
            'id': perm.id,
            'entity_type_id': perm.entity_type_id,
            'entity_type_name': perm.entity_type.name,
            'can_read': perm.can_read,
            'can_create': perm.can_create,
            'can_update': perm.can_update,
            'can_delete': perm.can_delete
        })
    
    return jsonify(result)

@access_control_bp.route('/role/<int:role_id>/permission', methods=['POST'])
@login_required
def update_permission(role_id):
    """Update or create permission for a role"""
    data = request.json
    entity_type_id = data.get('entity_type_id')
    
    try:
        # Find or create permission
        permission = EntityPermission.query.filter_by(
            role_id=role_id,
            entity_type_id=entity_type_id
        ).first()
        
        if not permission:
            permission = EntityPermission(
                role_id=role_id,
                entity_type_id=entity_type_id
            )
            db.session.add(permission)
        
        # Update permissions
        permission.can_read = data.get('can_read', False)
        permission.can_create = data.get('can_create', False)
        permission.can_update = data.get('can_update', False)
        permission.can_delete = data.get('can_delete', False)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Permission updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@access_control_bp.route('/user/<int:user_id>/roles')
@login_required  
def get_user_roles(user_id):
    """Get roles assigned to a user"""
    user = User.query.get_or_404(user_id)
    roles = [{'id': ur.role.id, 'name': ur.role.name} for ur in user.user_roles]
    return jsonify(roles)

@access_control_bp.route('/user/<int:user_id>/assign-role', methods=['POST'])
@login_required
def assign_role(user_id):
    """Assign role to user"""
    data = request.json
    role_id = data.get('role_id')
    
    try:
        # Check if already assigned
        existing = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
        if existing:
            return jsonify({'success': False, 'error': 'Role already assigned'}), 400
        
        user_role = UserRole(user_id=user_id, role_id=role_id)
        db.session.add(user_role)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Role assigned successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@access_control_bp.route('/user/<int:user_id>/remove-role/<int:role_id>', methods=['DELETE'])
@login_required
def remove_role(user_id, role_id):
    """Remove role from user"""
    try:
        user_role = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first()
        if user_role:
            db.session.delete(user_role)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Role removed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Role assignment not found'}), 404
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@access_control_bp.route('/users/create', methods=['POST'])
@login_required
def create_user():
    """Create a new user"""
    data = request.json
    
    try:
        # Validate required fields
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'success': False, 'error': 'Username, email, and password are required'}), 400
        
        # Check if username already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        # Check if email already exists
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'Email already exists'}), 400
        
        # Create user
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            password=generate_password_hash(data['password']),
            is_active=data.get('is_active', True)
        )
        db.session.add(user)
        db.session.flush()
        
        # Assign roles if provided
        role_ids = data.get('role_ids', [])
        if role_ids:
            for role_id in role_ids:
                user_role = UserRole(user_id=user.id, role_id=int(role_id))
                db.session.add(user_role)
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'user_id': user.id,
            'message': 'User created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@access_control_bp.route('/roles/create', methods=['POST'])
@login_required
def create_role():
    """Create a new role"""
    data = request.json
    
    try:
        # Validate required fields
        if not data.get('code') or not data.get('name'):
            return jsonify({'success': False, 'error': 'Code and name are required'}), 400
        
        # Check if code already exists
        if Role.query.filter_by(code=data['code']).first():
            return jsonify({'success': False, 'error': 'Role code already exists'}), 400
        
        # Create role
        role = Role(
            code=data['code'],
            name=data['name'],
            description=data.get('description', ''),
            is_system=False,
            is_active=data.get('is_active', True)
        )
        db.session.add(role)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'role_id': role.id, 
            'message': 'Role created successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500