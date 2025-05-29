from typing import TypeVar, Union, Any, Dict

# Tipo personalizado para valores numéricos do psutil
PsutilValue = TypeVar('PsutilValue', int, float, Any)

# Tipo para valores de porcentagem
PercentageValue = Union[int, float]

# Tipo para status do sistema
SystemStatus = Dict[str, Union[str, Dict[str, Union[str, float]]]] 