"""Retrieval 패키지.

!! 아래 import는 순서가 의미를 갖는다. 지우거나 옮기지 말 것 !!

Windows + Anaconda 환경에서 torch를 numpy보다 먼저 import하면 OpenMP 런타임이
두 번 초기화되면서 프로세스가 즉사한다:

    OMP: Error #15: Initializing libiomp5md.dll, but found libiomp5md.dll
    already initialized.

torch가 자체 libiomp5md.dll을 들고 오는데 Anaconda의 MKL도 같은 DLL을 쓰기
때문이다. numpy를 먼저 로드해 OpenMP를 한 번만 초기화시키면 torch가 그것을
재사용한다. 실측 결과:

    torch 단독              -> 실패
    torch -> faiss          -> 실패
    faiss -> torch          -> 정상
    numpy -> torch -> faiss -> 정상

흔히 쓰이는 KMP_DUPLICATE_LIB_OK=TRUE 우회는 채택하지 않았다. 그 플래그의
공식 경고문에 "may cause crashes or silently produce incorrect results"가
붙어 있는데, 조용히 틀린 검색 결과를 내는 것은 안전 판정 시스템에서
허용할 수 없는 실패 모드다.
"""

import numpy  # noqa: F401  (import 순서 고정용. 미사용처럼 보여도 제거 금지)
