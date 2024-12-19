from hashlib import md5
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from typing import Optional
from datetime import timedelta

import secrets
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from app import db
from app import login
from flask import url_for

followers = sa.Table('followers', db.metadata, 
         sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True), 
         sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True))


class PaginatedAPIMixin(object):
    @staticmethod
    def to_collection_dict(query, page, per_page, endpoint, **kwargs):
        resources = db.paginate(query, page=page, per_page=per_page,
                                error_out=False)
        data = {
            'items': [item.to_dict() for item in resources.items],
            '_meta': {
                'page': page,
                'per_page': per_page,
                'total_pages': resources.pages,
                'total_items': resources.total
            },
            '_links': {
                'self': url_for(endpoint, page=page, per_page=per_page,
                                **kwargs),
                'next': url_for(endpoint, page=page + 1, per_page=per_page,
                                **kwargs) if resources.has_next else None,
                'prev': url_for(endpoint, page=page - 1, per_page=per_page,
                                **kwargs) if resources.has_prev else None
            }
        }
        return data
    
class User(PaginatedAPIMixin, UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    posts: so.WriteOnlyMapped['Post'] = so.relationship(back_populates='author')
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))
    
    following: so.WriteOnlyMapped['User'] = so.relationship(back_populates='followers', secondary=followers, 
                                                            primaryjoin=(followers.c.follower_id == id),
                                                            secondaryjoin=(followers.c.followed_id == id))
    followers: so.WriteOnlyMapped['User'] = so.relationship(back_populates='following', secondary=followers, 
                                                            primaryjoin=(followers.c.followed_id == id),
                                                            secondaryjoin=(followers.c.follower_id == id))
    token: so.Mapped[Optional[str]] = so.mapped_column(sa.String(32), index=True, unique=True)
    token_expiration: so.Mapped[Optional[datetime]]

    def __repr__(self):
        return '<User {}>'.format(self.username)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'
    
    def is_following(self, user):
        query = self.following.select().where(User.id==user.id)
        return db.session.scalar(query)

    def follow(self, user):
        if not self.is_following(user):
            self.following.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.following.remove(user)

    def followers_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.followers.select().subquery())
        return db.session.scalar(query)
        
    def following_count(self):
        query = sa.select(sa.func.count()).select_from(self.following.select().subquery())
        return db.session.scalar(query)
    
    def following_posts(self):
        Author = so.aliased(User)
        Follower = so.aliased(User)
        # return sa.select(Post)\
        #         .join(Post.author.of_type(Author))\
        #         .join(Author.followers.of_type(Follower))\
        #         .where(sa.or_(Follower.id == self.id, Author.id == self.id))\
        #         .group_by(Post)\
        #         .order_by(Post.timestamp.desc())
    
        return (
            sa.select(Post)
            .join(Post.author.of_type(Author))
            .join(Author.followers.of_type(Follower), isouter=True)
            .where(sa.or_(
                Follower.id == self.id,
                Author.id == self.id,
            ))
            .group_by(Post)
            .order_by(Post.timestamp.desc())
        )
    
    def post_count(self):
        query = sa.select(sa.func.count()).select_from(
            self.posts.select().subquery())
        return db.session.scalar(query)
        # return len(self.posts.all())
    
    def to_dict(self, include_email=False):
        data = {"id":self.id,
                "username": self.username,
                'last_seen': self.last_seen.replace(
                        tzinfo=timezone.utc).isoformat() if self.last_seen else None,
                'about_me': self.about_me,
                'post_count': self.post_count(),
                'follower_count': self.followers_count(),
                'following_count': self.following_count(),
                '_links': {
                    'self': url_for('api.get_user', id=self.id),
                    'followers': url_for('api.get_followers', id=self.id),
                    'following': url_for('api.get_following', id=self.id),
                    'avatar': self.avatar(128)
                }
        }
        if include_email:
            data['email'] = self.email
        return data

    def from_dict(self, data, new_user=False):
        for field in ['username', 'email', 'about_me']:
            if field in data:
                setattr(self, field, data[field])
        if new_user and 'password' in data:
            self.set_password(data['password'])

    def get_token(self, expires_in=3600):
        # Return a token for user
        now = datetime.now(timezone.utc)
        if self.token and self.token_expiration.replace(tzinfo=timezone.utc) > now + timedelta(seconds=60):
            return self.token
        self.token = secrets.token_hex(16)
        self.token_expiration = now + timedelta(seconds=expires_in)
        db.session.add(self) # Change the object's attribute if object existed, else create new object.
        return self.token
    
    def revoke_token(self):
        # Make the token assigned to the user invalid
        self.token_expiration = datetime.now(timezone.utc) - timedelta(seconds=1)

    @staticmethod
    def check_token(token):
        # Take a token as input and returns the user this token belongs to as a response
        user = db.session.scalar(sa.select(User).where(User.token == token))
        
        # Check if the token is invalid or expired
        if user is None or user.token_expiration.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return None
        return user

class Post(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), index=True)
    author: so.Mapped[User] = so.relationship(back_populates='posts')
    language: so.Mapped[Optional[str]] = so.mapped_column(sa.String(5))

    def __repr__(self):
        return '<Post {}>'. format(self.body)



@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

