from flask import Flask, render_template, request, jsonify
from binance.client import Client
import pandas as pd
import requests

app = Flask(__name__)

# Binance API Keys
BINANCE_API_KEY = ''
BINANCE_API_SECRET = ''

# Etherscan API Key
ETHERSCAN_API_KEY = ''

# Initialize Binance Client
client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)

@app.route('/')
def home():
    return render_template('index.html')

# Binance Wallet Balances
@app.route('/get_balances', methods=['GET'])
def get_balances():
    try:
        # Spot wallet balances
        spot_balances = client.get_account()
        spot_wallet_df = pd.DataFrame(spot_balances['balances'])
        spot_wallet_df['free'] = spot_wallet_df['free'].astype(float)
        spot_wallet_df['locked'] = spot_wallet_df['locked'].astype(float)
        spot_wallet_df['total'] = spot_wallet_df['free'] + spot_wallet_df['locked']
        spot_wallet_df = spot_wallet_df[spot_wallet_df['total'] > 0]
        spot_wallet_df = spot_wallet_df[['asset', 'free', 'locked', 'total']]

        # Funding wallet balances
        funding_balances = client.funding_wallet()
        funding_wallet_df = pd.DataFrame(funding_balances)
        funding_wallet_df['free'] = funding_wallet_df['free'].astype(float)
        funding_wallet_df['locked'] = 0.0
        funding_wallet_df['total'] = funding_wallet_df['free']
        funding_wallet_df = funding_wallet_df[funding_wallet_df['total'] > 0]
        funding_wallet_df = funding_wallet_df[['asset', 'free', 'locked', 'total']]

        # Combine balances
        combined_df = pd.concat([spot_wallet_df, funding_wallet_df], ignore_index=True)

        return combined_df.to_json(orient='records')

    except Exception as e:
        return jsonify({"error": str(e)})

# Binance Transactions
@app.route('/get_transactions/<asset>', methods=['GET'])
def get_transactions(asset):
    try:
        deposits = client.get_deposit_history(asset=asset)
        withdrawals = client.get_withdraw_history(asset=asset)

        deposits_df = pd.DataFrame(deposits['depositList'])
        withdrawals_df = pd.DataFrame(withdrawals['withdrawList'])

        if not deposits_df.empty:
            deposits_df['type'] = 'Deposit'
            deposits_df['status'] = deposits_df['status'].replace({1: "Completed"})
        if not withdrawals_df.empty:
            withdrawals_df['type'] = 'Withdrawal'
            withdrawals_df['status'] = withdrawals_df['status'].replace({5: "Completed", 4: "Cancelled"})

        transactions = pd.concat([deposits_df, withdrawals_df], ignore_index=True)
        if not transactions.empty:
            transactions['insertTime'] = pd.to_datetime(transactions['insertTime'], unit='ms')
            transactions = transactions[['type', 'amount', 'status', 'insertTime']]
        return transactions.to_json(orient='records')

    except Exception as e:
        return jsonify({"error": str(e)})

# Etherscan Wallet Balances and Transactions
@app.route('/get_etherscan_data/<wallet_address>', methods=['GET'])
def get_etherscan_data(wallet_address):
    try:
        # Fetch ETH balance
        balance_url = f"https://api.etherscan.io/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={ETHERSCAN_API_KEY}"
        balance_response = requests.get(balance_url).json()
        eth_balance = int(balance_response['result']) / 10**18  # Convert Wei to ETH

        # Fetch transaction history
        tx_url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet_address}&startblock=0&endblock=99999999&sort=asc&apikey={ETHERSCAN_API_KEY}"
        tx_response = requests.get(tx_url).json()
        transactions = tx_response.get('result', [])

        # Return combined data
        return jsonify({"balance": eth_balance, "transactions": transactions})

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(debug=True)
