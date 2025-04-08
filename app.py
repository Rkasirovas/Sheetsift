import os
import pandas as pd
from flask import Flask, render_template, request, redirect, send_file, url_for

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/apie')
def apie():
    return render_template('apie.html')

@app.route('/kontaktai')
def kontaktai():
    return render_template('kontaktai.html')

@app.route('/sekmingai')
def sekmingai():
    return render_template('sekmingai.html')

@app.route('/sekmingai/atsisiusti')
def atsisiusti():
    path = os.path.join(app.config['RESULT_FOLDER'], 'Apdoroti_Israsai.xlsx')
    return send_file(path, as_attachment=True)

@app.route('/analyze', methods=['POST'])
def analyze():
    bank = request.form.get('bank')
    if bank == 'seb':
        return analyze_seb()
    elif bank == 'swedbank':
        return analyze_swedbank()
    # elif bank == 'siauliubankas':
    #     return analyze_siauliubankas()
    else:
        return "Pasirinktas bankas šiuo metu nepalaikomas!", 400

def analyze_seb():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        df = pd.read_excel(filepath)

        df["METAI"] = pd.to_datetime(df["DATA"], errors="coerce").dt.year
        df['MOKĖTOJO ARBA GAVĖJO PAVADINIMAS'] = df['MOKĖTOJO ARBA GAVĖJO PAVADINIMAS'].fillna('Nenurodytas')
        df['SĄSKAITA'] = df['SĄSKAITA'].fillna('Sąskaita nenurodyta')
        df['MOKĖJIMO PASKIRTIS'] = df['MOKĖJIMO PASKIRTIS'].fillna('Be paskirties')
        df['SĄSKAITOS NR'] = df['SĄSKAITOS NR'].fillna('Sąskaita nenurodyta')

        credit_df = df[df['DEBETAS/KREDITAS'] == 'C']

        credit_pivot = credit_df.pivot_table(index=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'],
                                             columns='METAI', values='SUMA', aggfunc='sum', fill_value=0).reset_index()

        credit_reasons = credit_df.groupby(['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA']) \
            ['MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

        credit_final = pd.merge(credit_pivot, credit_reasons,
                                on=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])

        credit_final = credit_final.rename(columns={
            'SĄSKAITOS NR': 'ASMENS SĄSKAITA',
            'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS': 'MOKĖTOJAS',
            'SĄSKAITA': 'MOKĖTOJO SĄSKAITA'
        })

        debit_df = df[df['DEBETAS/KREDITAS'] == 'D']

        debit_pivot = debit_df.pivot_table(index=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'],
                                           columns='METAI', values='SUMA', aggfunc='sum', fill_value=0).reset_index()

        debit_reasons = debit_df.groupby(['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA']) \
            ['MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

        debit_final = pd.merge(debit_pivot, debit_reasons,
                               on=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])

        debit_final = debit_final.rename(columns={
            'SĄSKAITOS NR': 'ASMENS SĄSKAITA',
            'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS': 'GAVĖJAS',
            'SĄSKAITA': 'GAVĖJO SĄSKAITA'
        })

        all_years = sorted(df['METAI'].dropna().unique())
        all_years = [int(y) for y in all_years if not pd.isna(y)]

        summary_list = []

        for account in df['SĄSKAITOS NR'].dropna().unique():
            account_credit = credit_df[credit_df['SĄSKAITOS NR'] == account]
            account_debit = debit_df[debit_df['SĄSKAITOS NR'] == account]

            credit_summary = account_credit.groupby('METAI')['SUMA'].sum()
            debit_summary = account_debit.groupby('METAI')['SUMA'].sum()
            credit_row = [credit_summary.get(year, 0) for year in all_years]
            debit_row = [debit_summary.get(year, 0) for year in all_years]
            credit_total = sum(credit_row)
            debit_total = sum(debit_row)
            credit_df_row = pd.DataFrame([credit_row + [credit_total]], columns=all_years + ['Viso'],
                                         index=[f'{account} Bendros Pajamos'])
            debit_df_row = pd.DataFrame([debit_row + [debit_total]], columns=all_years + ['Viso'],
                                        index=[f'{account} Bendros Išlaidos'])
            summary_list.append(credit_df_row)
            summary_list.append(debit_df_row)

        summary_combined = pd.concat(summary_list)

        result_path = os.path.join(app.config['RESULT_FOLDER'], 'Apdoroti_Israsai.xlsx')
        with pd.ExcelWriter(result_path, engine='xlsxwriter') as writer:
            credit_final.to_excel(writer, sheet_name='Pajamos', index=False)
            debit_final.to_excel(writer, sheet_name='Islaidos', index=False)
            summary_combined.to_excel(writer, sheet_name='Bendra')

        return redirect(url_for('sekmingai'))

    return "KLAIDA: Neteisingas failo formatas. Bandykite dar kartą!", 400


def analyze_swedbank():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)

        df = pd.read_excel(filepath)




if __name__ == '__main__':
    app.run(debug=True)
