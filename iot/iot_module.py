from . import ABCSAdapter
from . import ELVAdapter
from . import GATEAdapter

module_list={
    "ABCS":ABCSAdapter.ABCS,
    "ELV":ELVAdapter.ELV,
    "GATE": GATEAdapter.GATE
}
