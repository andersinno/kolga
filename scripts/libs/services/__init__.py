from typing import Dict, Type

from scripts.libs.service import Service
from scripts.libs.services.mysql import MysqlService
from scripts.libs.services.postresql import PostgresqlService
from scripts.libs.services.rabbitmq import RabbitmqService
from scripts.utils.general import MYSQL, POSTGRES, RABBITMQ

services: Dict[str, Type[Service]] = {
    MYSQL: MysqlService,
    POSTGRES: PostgresqlService,
    RABBITMQ: RabbitmqService,
}
