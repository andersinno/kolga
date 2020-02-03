from typing import Dict, Type

from scripts.libs.service import Service
from scripts.libs.services.mysql import MysqlService
from scripts.libs.services.postresql import PostgresqlService
from scripts.utils.general import MYSQL, POSTGRES

services: Dict[str, Type[Service]] = {
    MYSQL: MysqlService,
    POSTGRES: PostgresqlService,
}
