from fastapi import APIRouter
from typing import Dict, List

router = APIRouter()

# Mapeamento de nomes de cursos do CED para os IDs de disciplinas na OM
CURSOS_OM: Dict[str, List[int]] = {
    "Mestre em Excel": [161, 197, 201, 560, 659],
    "Video Creator Profissional": [138, 240, 169, 254],
    "Design Gráfico Profissional": [751, 169, 822, 78, 441],
    "Programador Master": [590, 176, 239, 203, 126, 252],
    "Desenvolvedor Web": [126, 239, 252, 237, 822],
    "Games Creator": [139, 124, 146, 473, 167],
    "Projetista Alto Nível": [135, 193, 195, 396, 541],
    "Administração de Pessoal": [156, 198, 214, 129],
    "Social Media Pro": [199, 780, 441, 202, 734, 264, 236],
    "Vendedor Digital": [123, 207, 236, 255, 222],
    "Crianças do Futuro": [92, 93, 94, 513, 568, 594, 705, 723, 782, 783, 837, 838],
    "Melhor Idade": [168, 599, 234, 627, 220],
    "Líder do Futuro": [154, 144, 214, 156, 129],
    "Auxiliar Contábil": [200, 183, 560, 129],
    "Auxiliar de Escritório": [754, 130, 160, 161, 162],
    "Segurança da Saúde": [271, 316, 334, 360, 426, 216],
    "Cuidador de Idosos": [276, 155, 271, 222],
    "Operador de Logística": [265, 161, 183, 201, 236],
    "Youtuber": [136, 240, 441, 264],
}


def obter_nomes_por_ids(ids: List[int]) -> List[str]:
    """Retorna os nomes de cursos correspondentes aos IDs fornecidos."""
    if not ids:
        return []

    ids_set = set(ids)

    # Verifica se existe algum curso com conjunto de IDs exatamente igual
    nomes_exatos = [n for n, lista in CURSOS_OM.items() if set(lista) == ids_set]
    if nomes_exatos:
        return nomes_exatos

    # Caso contrário, inclui nomes de cursos que contenham qualquer um dos IDs
    nomes: List[str] = []
    for cid in ids:
        for nome, lista in CURSOS_OM.items():
            if cid in lista and nome not in nomes:
                nomes.append(nome)

    return nomes

# Aceita /cursos e /cursos/
@router.get("", summary="Lista de cursos disponíveis")
@router.get("/", summary="Lista de cursos disponíveis")
async def listar_cursos():
    """Retorna o mapeamento de cursos do CED para as disciplinas da OM."""
    return {"cursos": CURSOS_OM}
