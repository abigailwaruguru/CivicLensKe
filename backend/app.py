#Flask Api
#import built-ins
import pandas 
import uuid
import os

#import from third-party
from flask_cors import CORS
from flask import Flask, request, jsonify, make_response
from dotenv import load_dotenv

#import own files
from storagecsv import storage
from rules import run_rules, compute_enforcements
from reports import generate_regulator_pack_csv, genereate_case_file_csv

load_dotenv()

app= Flask(__name__)
CORS(app) #Allows frontend to call API

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "civiclens-admin")

#Convert different repressentations of true/false into python boolean
def _parse_bool(val):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "yes", "1")
    return bool (val) #Else False

#POST / Transactions
@app.route("/transactions", methods=["POST"])
#def submit_transaction():