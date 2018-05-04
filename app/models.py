import jwt
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, request, url_for
from . import db


class Permission:
    ADMIN = 1
    USER = 21
    LIST_USERS = 22
    ADD_USER = 23
    Edit_USER = 24
    DELETE_USER = 25
    BLOCK_USER = 26


class Role(db.Model):
    """This class reprsents the role table."""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User': [
                # TODO
            ],
            'Developer': [
                Permission.LIST_USERS
            ],
            'QA': [
                Permission.LIST_USERS,
                Permission.ADD_USER,
                Permission.Edit_USER,
                Permission.BLOCK_USER
            ],
            'Administrator': [
                Permission.ADMIN,

                Permission.LIST_USERS,
                Permission.ADD_USER,
                Permission.Edit_USER,
                Permission.DELETE_USER,
                Permission.BLOCK_USER,

            ]
        }

        default_role = 'User'

        for r in roles:
            role = Role.query.filter_by(title=r).first()
            if role is None:
                role = Role(title=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.title == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.title


class User(db.Model):
    """This class represents the user table."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, index=True)
    password = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    status = db.Column(db.Integer, default=1)
    last_login_at = db.Column(db.DateTime, default=None)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, default=None)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.name == current_app.config.get('APP_ROOT_ADMIN'):
                self.role = Role.query.filter_by(title='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()

    @staticmethod
    def insert_root_admin():
        user = User(name='sysop',
                    password=generate_password_hash('Passw0rd!'),
                    role_id=Role.query.filter_by(title='Administrator').first())

        db.session.add(user)
        db.session.commit()

    def verify_password(self, password):
        return check_password_hash(self.password, password)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def encode_auth_token(self):
        try:
            payload = {
                'exp': datetime.utcnow() + timedelta(days=0, minutes=current_app.config.get('JWT_TTL')),
                'iat': datetime.utcnow(),
                'sub': self.id
            }
            return jwt.encode(
                payload,
                current_app.config['JWT_SECRET'],
                algorithm='HS256'
            )
        except Exception as e:
            return e

    @staticmethod
    def decode_auth_token(token):
        try:
            payload = jwt.decode(token, current_app.config.get('JWT_SECRET'))
            return payload['sub']
        except jwt.ExpiredSignatureError:
            return 'Token expired. Please login again.'
        except jwt.InvalidTokenError:
            return 'Invalid token. Please login again.'

    def __repr__(self):
        return '<User %r>' % self.name


class Log(db.Model):
    """logs"""
    __tablename__ = 'logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Log %r>' % self.action


class App(db.Model):
    """apps"""
    __tablename__ = 'apps'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20), unique=True, nullable=False)
    slug = db.Column(db.String(20), unique=True, nullable=False)
    version = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.SmallInteger, default=1)       # 1 Web, 2 APP, 3 PC, 4 other
    auth_type = db.Column(db.SmallInteger, default=0)  # 0 No Auth, 1 Basic Auth, 2 OAuth 2.0
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, default=None)

    def __repr__(self):
        return '<App %r>' % self.title


class ApiGroup(db.Model):
    """api_groups"""
    __tablename__ = 'api_groups'

    id = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer, nullable=False,)
    title = db.Column(db.String(20))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<ApiGroup %r>' % self.title


class Api(db.Model):
    """apis"""
    __tablename__ = 'apis'

    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.Integer, db.ForeignKey('apps.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('api_groups.id'))
    title = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(256), nullable=False)
    method = db.Column(db.String(10), nullable=False, default='GET')
    headers = db.Column(db.Text, nullable=True)
    need_auth = db.Column(db.Boolean, default=0)    # 0 No auth required, 1 auth required
    status = db.Column(db.SmallInteger, default=1)  # 1, 2, 3
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, default=None)

    def __repr__(self):
        return '<Api %r>' % self.title


class ApiResponse(db.Model):
    """api_responses"""
    __tablename__ = 'api_responses'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(20))

    def __repr__(self):
        return '<ApiResponse %r>' % self.key


class ApiExample(db.Model):
    """api_examples"""
    __tablename__ = 'api_examples'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20))

    def __repr__(self):
        return '<ApiExample %r>' % self.title