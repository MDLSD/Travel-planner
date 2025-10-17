# ТиВПО практика 3



библиотеки:
pip install fastapi uvicorn\[standard] httpx python-dotenv



установка



git clone https://github.com/MDLSD/Travel-planner.git



cd Travel-planner



python -m venv .venv



.venv\\Scripts\\activate



pip install fastapi uvicorn\[standard] httpx python-dotenv



echo VALHALLA\_URL=http://localhost:8002/route > .env



uvicorn app:app --reload



\# http://127.0.0.1:8000



