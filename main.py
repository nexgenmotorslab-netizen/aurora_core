from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from reportlab.pdfgen import canvas

DATABASE_URL = "sqlite:///./aurora.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String)
    user_name = Column(String)  # NEW
    amount = Column(Float)
    risk_score = Column(Integer)
    flagged = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="AURORA CORE API v7.1")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TransactionIn(BaseModel):
    user_id: str
    user_name: str  # NEW
    amount: float


@app.post("/api/v1/transactions/screen")
def screen_transaction(tx: TransactionIn, db: Session = Depends(get_db)):
    # NEW SMART RISK LOGIC
    if tx.amount > 50000:
        risk = 10
        flagged = True
    elif tx.amount > 10000:
        risk = 6
        flagged = False
    else:
        risk = 2
        flagged = False

    db_tx = Transaction(
        user_id=tx.user_id,
        user_name=tx.user_name,
        amount=tx.amount,
        risk_score=risk,
        flagged=flagged,
    )
    db.add(db_tx)
    db.commit()
    return {
        "status": "screened",
        "user": tx.user_name,
        "risk_score": risk,
        "flagged": flagged,
    }


@app.get("/api/v1/reports/compliance.pdf")
def download_compliance_report(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).all()
    filename = f"compliance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
    c = canvas.Canvas(filename)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 800, "AURORA CORE - COMPLIANCE REPORT")
    c.setFont("Helvetica", 10)
    c.drawString(100, 780, f"Generated: {datetime.now()}")
    y = 750
    c.drawString(50, y, "ID | Customer Name | User ID | Amount GHS | Risk | Status")
    y -= 20
    for tx in transactions:
        status = "FLAGGED" if tx.flagged else "CLEAR"
        c.drawString(
            50,
            y,
            f"{tx.id} | {tx.user_name} | {tx.user_id} | {tx.amount} | {tx.risk_score} | {status}",
        )
        y -= 20
    c.save()
    return FileResponse(filename, filename=filename)


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "version": "7.1", "trusted": True}
