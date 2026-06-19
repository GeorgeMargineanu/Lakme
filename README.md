# Rețetele lui Lakme

Un marketplace Flask pentru cele 22 de rețete vegetariene Lakme. Rețetele pot fi filtrate după zonă și bucătărie, cumpărate individual cu $1 și descărcate ca PDF separat după checkout.

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Deschide `http://127.0.0.1:5000`.

## Notă despre plată

Checkout-ul inclus este intenționat un demo local: acceptă date fictive, nu stochează datele cardului și nu încasează bani. Înainte de publicare, înlocuiește POST-ul de checkout cu un procesator precum Stripe Checkout și setează `SECRET_KEY` printr-o variabilă de mediu.
