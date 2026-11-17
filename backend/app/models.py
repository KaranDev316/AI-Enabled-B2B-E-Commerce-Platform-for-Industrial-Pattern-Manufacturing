from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, Enum):
    ADMIN = 'admin'
    EMPLOYEE = 'employee'
    CUSTOMER = 'customer'


class RFQType(str, Enum):
    STANDARD = 'standard'
    CUSTOM = 'custom'


class RFQStatus(str, Enum):
    SUBMITTED = 'submitted'
    UNDER_REVIEW = 'under_review'
    QUOTED = 'quoted'
    REJECTED = 'rejected'
    CLOSED = 'closed'


class TicketType(str, Enum):
    INQUIRY = 'inquiry'
    COMPLAINT = 'complaint'
    ORDER_ISSUE = 'order_issue'
    TECHNICAL_SUPPORT = 'technical_support'


class TicketStatus(str, Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(String(50), nullable=False, default=UserRole.CUSTOMER.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer_profile: Mapped[Optional['CustomerProfile']] = relationship(
        'CustomerProfile', back_populates='user', uselist=False, cascade='all, delete-orphan'
    )
    employee_profile: Mapped[Optional['EmployeeProfile']] = relationship(
        'EmployeeProfile', back_populates='user', uselist=False, cascade='all, delete-orphan'
    )
    sessions: Mapped[list['Session']] = relationship(
        'Session', back_populates='user', cascade='all, delete-orphan'
    )
    rfqs: Mapped[list['RFQ']] = relationship(
        'RFQ', back_populates='customer', cascade='all, delete-orphan'
    )
    uploaded_files: Mapped[list['RFQFile']] = relationship(
        'RFQFile', back_populates='uploader'
    )
    orders: Mapped[list['Order']] = relationship(
        'Order', back_populates='customer', cascade='all, delete-orphan'
    )
    support_tickets: Mapped[list['SupportTicket']] = relationship(
        'SupportTicket', back_populates='customer', cascade='all, delete-orphan'
    )
    support_messages: Mapped[list['SupportMessage']] = relationship(
        'SupportMessage', back_populates='sender', cascade='all, delete-orphan'
    )


class CustomerProfile(Base):
    __tablename__ = 'customer_profiles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    gstin: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped['User'] = relationship('User', back_populates='customer_profile')


class EmployeeProfile(Base):
    __tablename__ = 'employee_profiles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped['User'] = relationship('User', back_populates='employee_profile')


class Session(Base):
    __tablename__ = 'sessions'

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped['User'] = relationship('User', back_populates='sessions')


class Category(Base):
    __tablename__ = 'categories'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    products: Mapped[list['Product']] = relationship('Product', back_populates='category')


class Product(Base):
    __tablename__ = 'products'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    material_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    indicative_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    category: Mapped[Optional['Category']] = relationship('Category', back_populates='products')
    rfqs: Mapped[list['RFQ']] = relationship('RFQ', back_populates='product')


class RFQ(Base):
    __tablename__ = 'rfqs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rfq_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False
    )
    rfq_type: Mapped[str] = mapped_column(String(50), nullable=False, default=RFQType.CUSTOM.value)
    product_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('products.id', ondelete='SET NULL'), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    material: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    dimensions: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    specifications: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_delivery_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=RFQStatus.SUBMITTED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped['User'] = relationship('User', back_populates='rfqs')
    product: Mapped[Optional['Product']] = relationship('Product', back_populates='rfqs')
    files: Mapped[list['RFQFile']] = relationship(
        'RFQFile', back_populates='rfq', cascade='all, delete-orphan', order_by='RFQFile.id'
    )


class RFQFile(Base):
    __tablename__ = 'rfq_files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rfq_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('rfqs.id', ondelete='CASCADE'), nullable=False, index=True
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    rfq: Mapped['RFQ'] = relationship('RFQ', back_populates='files')
    uploader: Mapped['User'] = relationship('User', back_populates='uploaded_files')


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False
    )
    rfq_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('rfqs.id', ondelete='SET NULL'), nullable=True
    )
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='pending_payment', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped['User'] = relationship('User', back_populates='orders')
    tickets: Mapped[list['SupportTicket']] = relationship('SupportTicket', back_populates='order')


class SupportTicket(Base):
    __tablename__ = 'support_tickets'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False
    )
    ticket_type: Mapped[str] = mapped_column(String(50), nullable=False, default=TicketType.INQUIRY.value)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=TicketStatus.OPEN.value)
    order_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('orders.id', ondelete='SET NULL'), nullable=True
    )
    rfq_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey('rfqs.id', ondelete='SET NULL'), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped['User'] = relationship('User', back_populates='support_tickets')
    order: Mapped[Optional['Order']] = relationship('Order', back_populates='tickets')
    rfq: Mapped[Optional['RFQ']] = relationship('RFQ')
    messages: Mapped[list['SupportMessage']] = relationship(
        'SupportMessage', back_populates='ticket', cascade='all, delete-orphan', order_by='SupportMessage.created_at'
    )
    attachments: Mapped[list['SupportTicketFile']] = relationship(
        'SupportTicketFile', back_populates='ticket', cascade='all, delete-orphan', order_by='SupportTicketFile.id'
    )


class SupportMessage(Base):
    __tablename__ = 'support_messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('support_tickets.id', ondelete='CASCADE'), index=True, nullable=False
    )
    sender_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False
    )
    sender_role: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    ticket: Mapped['SupportTicket'] = relationship('SupportTicket', back_populates='messages')
    sender: Mapped['User'] = relationship('User', back_populates='support_messages')


class SupportTicketFile(Base):
    __tablename__ = 'support_ticket_files'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('support_tickets.id', ondelete='CASCADE'), index=True, nullable=False
    )
    uploaded_by_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    ticket: Mapped['SupportTicket'] = relationship('SupportTicket', back_populates='attachments')
    uploader: Mapped['User'] = relationship('User')

