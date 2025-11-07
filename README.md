ТиВПО практика 3
библиотеки: pip install fastapi uvicorn[standard] httpx python-dotenv

установка

git clone https://github.com/MDLSD/Travel-planner.git

cd Travel-planner

python -m venv .venv

.venv\Scripts\activate

pip install fastapi uvicorn[standard] httpx python-dotenv

$env:ORS_API_KEY="eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjIwNzA1OTVjNmUxNzQ1MWI4OTZhMDQyNzM2NDg2ZjZhIiwiaCI6Im11cm11cjY0In0="

uvicorn app:app --reload

http://127.0.0.1:8000
