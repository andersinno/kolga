from typing import Dict, Type

from kolga.libs.service import Service
from kolga.libs.services.mysql import MysqlService
from kolga.libs.services.postresql import PostgresqlService
from kolga.libs.services.rabbitmq import RabbitmqService
from kolga.utils.general import MYSQL, POSTGRES, RABBITMQ

services: Dict[str, Type[Service]] = {
    MYSQL: MysqlService,
    POSTGRES: PostgresqlService,
    RABBITMQ: RabbitmqService,
}
