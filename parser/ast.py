from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass
class SourceLocation:
    line: int = 0
    column: int = 0

@dataclass
class ASTNode:
    location: SourceLocation = field(default_factory=SourceLocation)

@dataclass
class Program(ASTNode):
    declarations: List[Any] = field(default_factory=list)

@dataclass
class Preprocessor(ASTNode):
    text: str = ""

@dataclass
class Property(ASTNode):
    name: str = ""
    value: str = ""

@dataclass
class Include(ASTNode):
    path: str = ""

@dataclass
class TypeRef(ASTNode):
    name: str = ""

@dataclass
class Literal(ASTNode):
    value: Any = None
    kind: str = ""

@dataclass
class Identifier(ASTNode):
    name: str = ""

@dataclass
class Parameter(ASTNode):
    type_name: str = ""
    name: str = ""
    default: Any = None

@dataclass
class VariableDeclaration(ASTNode):
    type_name: str = ""
    name: str = ""
    initializer: Any = None
    is_input: bool = False
    is_const: bool = False
    is_static: bool = False

@dataclass
class FunctionDeclaration(ASTNode):
    return_type: str = ""
    name: str = ""
    parameters: List[Parameter] = field(default_factory=list)
    body: Any = None

@dataclass
class Block(ASTNode):
    statements: List[Any] = field(default_factory=list)

@dataclass
class IfStatement(ASTNode):
    condition: Any = None
    then_branch: Any = None
    else_branch: Any = None

@dataclass
class ReturnStatement(ASTNode):
    expression: Any = None

@dataclass
class ExpressionStatement(ASTNode):
    expression: Any = None

@dataclass
class Assignment(ASTNode):
    target: Any = None
    value: Any = None
    operator: str = "="

@dataclass
class CallExpression(ASTNode):
    callee: Any = None
    arguments: List[Any] = field(default_factory=list)

@dataclass
class BinaryExpression(ASTNode):
    left: Any = None
    operator: str = ""
    right: Any = None

@dataclass
class UnaryExpression(ASTNode):
    operator: str = ""
    operand: Any = None

@dataclass
class MemberAccess(ASTNode):
    object: Any = None
    member: str = ""

@dataclass
class ArrayAccess(ASTNode):
    array: Any = None
    index: Any = None

@dataclass
class WarningNode(ASTNode):
    code: str = ""
    message: str = ""

EVENT_FUNCTIONS = {
    "OnInit", "OnDeinit", "OnTick", "OnTimer", "OnTrade",
    "OnTradeTransaction", "OnBookEvent", "OnChartEvent",
    "OnTester", "OnTesterInit", "OnTesterPass", "OnTesterDeinit",
    "OnStart", "OnCalculate"
}

def is_event_function(name: str) -> bool:
    return name in EVENT_FUNCTIONS
