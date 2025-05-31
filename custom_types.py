"""
Tipos personalizados para o Dashboard Renov.
Este módulo contém as definições de tipos personalizados utilizados na aplicação.
"""

from typing import TypeVar, TypedDict, Literal, Union

# Tipos básicos
PsutilValue = TypeVar('PsutilValue', float, int)
PercentageValue = float

# Status de recursos do sistema
class ResourceStatus(TypedDict):
    value: float
    status: Literal['ok', 'warning', 'critical']

# Status do banco de dados
class DatabaseStatus(TypedDict):
    status: Literal['ok', 'error']

# Status geral do sistema
class SystemStatus(TypedDict):
    status: Literal['healthy', 'unhealthy', 'error']
    cpu: ResourceStatus
    memory: ResourceStatus
    disk: ResourceStatus
    database: DatabaseStatus
    message: Union[str, None] 