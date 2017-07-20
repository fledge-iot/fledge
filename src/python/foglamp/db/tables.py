# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

"""FogLamp Database Table Definitions
"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, MetaData, SmallInteger, String, Table, Time, text
from sqlalchemy.dialects.postgresql.base import INET, INTERVAL, UUID
from sqlalchemy.dialects.postgresql import JSONB


__author__ = "Amarendra Kumar Sinha"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"


db_connection_url = "dbname='foglamp'"
# 'postgresql://foglamp:foglamp@localhost:5432/foglamp'

metadata = MetaData()

t_asset_links = Table(
    'asset_links', metadata,
    Column('link_id', ForeignKey('links.id'), primary_key=True, nullable=False, index=True),
    Column('asset_id', ForeignKey('assets.id'), primary_key=True, nullable=False, index=True),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_asset_message_status = Table(
    'asset_message_status', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('asset_message_status_id_seq'::regclass)")),
    Column('description', String(255), nullable=False, server_default=text("''::character varying"))
)


t_asset_messages = Table(
    'asset_messages', metadata,
    Column('id', BigInteger, primary_key=True, server_default=text("nextval('asset_messages_id_seq'::regclass)")),
    Column('asset_id', ForeignKey('assets.id'), nullable=False, index=True),
    Column('status_id', ForeignKey('asset_message_status.id'), nullable=False, index=True),
    Column('message', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_asset_status = Table(
    'asset_status', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('asset_status_id_seq'::regclass)")),
    Column('descriprion', String(255), nullable=False, server_default=text("''::character varying"))
)


t_asset_status_changes = Table(
    'asset_status_changes', metadata,
    Column('id', BigInteger, primary_key=True, server_default=text("nextval('asset_status_changes_id_seq'::regclass)")),
    Column('asset_id', ForeignKey('assets.id'), nullable=False, index=True),
    Column('status_id', ForeignKey('asset_status.id'), nullable=False, index=True),
    Column('log', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('start_ts', DateTime(True), nullable=False),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_asset_types = Table(
    'asset_types', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('asset_types_id_seq'::regclass)")),
    Column('description', String(255), nullable=False, server_default=text("''::character varying"))
)


t_assets = Table(
    'assets', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('assets_id_seq'::regclass)")),
    Column('code', String(50), unique=True),
    Column('description', String(255), nullable=False, server_default=text("''::character varying")),
    Column('type_id', ForeignKey('asset_types.id'), nullable=False, index=True),
    Column('address', INET, nullable=False, server_default=text("'0.0.0.0'::inet")),
    Column('status_id', ForeignKey('asset_status.id'), nullable=False, index=True),
    Column('properties', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('has_readings', Boolean, nullable=False, server_default=text("false")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_configuration = Table(
    'configuration', metadata,
    Column('key', String(10), primary_key=True),
    Column('description', String(255), nullable=False),
    Column('value', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_configuration_changes = Table(
    'configuration_changes', metadata,
    Column('key', String(10), primary_key=True, nullable=False),
    Column('configuration_ts', DateTime(True), primary_key=True, nullable=False),
    Column('configuration_value', JSON, nullable=False),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_destinations = Table(
    'destinations', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('destinations_id_seq'::regclass)")),
    Column('type', SmallInteger, nullable=False, server_default=text("1")),
    Column('description', String(255), nullable=False, server_default=text("''::character varying")),
    Column('properties', JSON, nullable=False, server_default=text("'{\"streaming\": \"all\"}'::jsonb")),
    Column('active_window', JSON, nullable=False, server_default=text("'[\"always\"]'::jsonb")),
    Column('active', Boolean, nullable=False, server_default=text("true")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_links = Table(
    'links', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('links_id_seq'::regclass)")),
    Column('asset_id', ForeignKey('assets.id'), nullable=False, index=True),
    Column('properties', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_log = Table(
    'log', metadata,
    Column('id', BigInteger, primary_key=True, server_default=text("nextval('log_id_seq'::regclass)")),
    Column('code', ForeignKey('log_codes.code'), nullable=False),
    Column('level', SmallInteger, nullable=False, server_default=text("0")),
    Column('log', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()")),
    Index('log_ix1', 'code', 'ts', 'level')
)


t_log_codes = Table(
    'log_codes', metadata,
    Column('code', String(5), primary_key=True),
    Column('description', String(80), nullable=False)
)


t_readings = Table(
    'readings', metadata,
    Column('id', BigInteger, primary_key=True, server_default=text("nextval('readings_id_seq'::regclass)")),
    Column('asset_code', String(50), nullable=False, index=True),
    Column('read_key', UUID, unique=True),
    Column('reading', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('user_ts', DateTime(True), nullable=False, server_default=text("now()")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_resources = Table(
    'resources', metadata,
    Column('id', BigInteger, primary_key=True, server_default=text("nextval('resources_id_seq'::regclass)")),
    Column('code', String(10), nullable=False, unique=True),
    Column('description', String(255), nullable=False, server_default=text("''::character varying"))
)


t_role_asset_permissions = Table(
    'role_asset_permissions', metadata,
    Column('role_id', ForeignKey('roles.id'), ForeignKey('roles.id'), primary_key=True, nullable=False, index=True),
    Column('asset_id', ForeignKey('assets.id'), primary_key=True, nullable=False, index=True),
    Column('access', JSON, nullable=False, server_default=text("'{}'::jsonb"))
)


t_role_resource_permission = Table(
    'role_resource_permission', metadata,
    Column('role_id', ForeignKey('roles.id'), primary_key=True, nullable=False, index=True),
    Column('resource_id', ForeignKey('resources.id'), primary_key=True, nullable=False, index=True),
    Column('access', JSON, nullable=False, server_default=text("'{}'::jsonb"))
)


t_roles = Table(
    'roles', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('roles_id_seq'::regclass)")),
    Column('name', String(25), nullable=False, unique=True),
    Column('description', String(255), nullable=False, server_default=text("''::character varying"))
)


t_scheduled_processes = Table(
    'scheduled_processes', metadata,
    Column('name', String(20), primary_key=True),
    Column('script', JSON)
)


t_schedules = Table(
    'schedules', metadata,
    Column('id', UUID, primary_key=True),
    Column('process_name', ForeignKey('scheduled_processes.name'), nullable=False),
    Column('schedule_name', String(20), nullable=False),
    Column('schedule_type', SmallInteger, nullable=False),
    Column('schedule_interval', INTERVAL),
    Column('schedule_time', Time),
    Column('schedule_day', SmallInteger),
    Column('exclusive', Boolean, nullable=False, server_default=text("false"))
)


t_statistics = Table(
    'statistics', metadata,
    Column('key', String(10), primary_key=True),
    Column('description', String(255), nullable=False),
    Column('value', BigInteger, nullable=False, server_default=text("0")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_statistics_history = Table(
    'statistics_history', metadata,
    Column('key', String(10), primary_key=True, nullable=False),
    Column('history_ts', DateTime(True), primary_key=True, nullable=False),
    Column('value', BigInteger, nullable=False, server_default=text("0")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_streams = Table(
    'streams', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('streams_id_seq'::regclass)")),
    Column('destination_id', ForeignKey('destinations.id'), nullable=False, index=True),
    Column('description', String(255), nullable=False, server_default=text("''::character varying")),
    Column('properties', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('object_stream', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('object_block', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('object_filter', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('active_window', JSON, nullable=False, server_default=text("'{}'::jsonb")),
    Column('active', Boolean, nullable=False, server_default=text("true")),
    Column('last_object', BigInteger, nullable=False, server_default=text("0")),
    Column('ts', DateTime(True), nullable=False, server_default=text("now()"))
)


t_tasks = Table(
    'tasks', metadata,
    Column('id', UUID, primary_key=True),
    Column('process_name', ForeignKey('scheduled_processes.name'), nullable=False),
    Column('state', SmallInteger, nullable=False),
    Column('start_time', DateTime(True), nullable=False, server_default=text("now()")),
    Column('end_time', DateTime(True)),
    Column('reason', String(255)),
    Column('pid', Integer, nullable=False),
    Column('exit_code', Integer)
)


t_user_asset_permissions = Table(
    'user_asset_permissions', metadata,
    Column('user_id', ForeignKey('users.id'), primary_key=True, nullable=False, index=True),
    Column('asset_id', ForeignKey('assets.id'), primary_key=True, nullable=False, index=True),
    Column('access', JSON, nullable=False, server_default=text("'{}'::jsonb"))
)


t_user_logins = Table(
    'user_logins', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('user_logins_id_seq'::regclass)")),
    Column('user_id', ForeignKey('users.id'), nullable=False, index=True),
    Column('ip', INET, nullable=False),
    Column('ts', DateTime(True), nullable=False)
)


t_user_resource_permissions = Table(
    'user_resource_permissions', metadata,
    Column('user_id', ForeignKey('users.id'), primary_key=True, nullable=False, index=True),
    Column('resource_id', ForeignKey('resources.id'), primary_key=True, nullable=False, index=True),
    Column('access', JSON, nullable=False, server_default=text("'{}'::jsonb"))
)


t_users = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True, server_default=text("nextval('users_id_seq'::regclass)")),
    Column('uid', String(80), nullable=False, unique=True),
    Column('role_id', ForeignKey('roles.id'), nullable=False, index=True),
    Column('description', String(255), nullable=False, server_default=text("''::character varying")),
    Column('pwd', String(255)),
    Column('public_key', String(255)),
    Column('access_method', SmallInteger, nullable=False, server_default=text("0"))
)
