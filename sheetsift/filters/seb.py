import pandas as pd
import re
import os
from flask import request, redirect, url_for, current_app, session
from sheetsift.utils import schedule_file_deletion

def analyze_seb():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)
            columns = df.columns

            selection = None

            if 'Nurašymo / įskaitymo data' and 'Operacijos aprašymas' and 'Suma sąskaitos valiuta' in columns:
                selection = 'old_seb'
                df["METAI"] = pd.to_datetime(df["Nurašymo / įskaitymo data"], errors="coerce").dt.year
                df['MOKĖJIMO PASKIRTIS'] = df['Operacijos aprašymas'].fillna('Nenurodytas')
                df['Suma'] = df['Suma sąskaitos valiuta'].astype(str).str.replace('EUR', '', regex=False).str.strip()
                df['Suma'] = pd.to_numeric(df['Suma'].str.replace(',', '.'), errors='coerce').fillna(0)

                def extract_info(text):
                    mok = re.search(r'(Lėšų nurašymas|Mokėtojas|Gavėjas)[:：]?\s*([^,]+)', text, re.IGNORECASE)
                    saskaita = re.search(r'(LT\d{18})', text)
                    return pd.Series({
                        'Mokėtojas/Gavėjas': mok.group(2).strip() if mok else 'Nenurodytas',
                        'Mokėtojo/Gavėjo sąskaita': saskaita.group(0) if saskaita else 'Sąskaita nenurodyta'
                    })

                df[['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaita']] = df['MOKĖJIMO PASKIRTIS'].apply(extract_info)

            elif 'DATA' and 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS' and 'SĄSKAITA' and 'MOKĖJIMO PASKIRTIS' and 'SĄSKAITOS NR' and 'DEBETAS/KREDITAS' in columns:
                selection = 'new_seb'
                df["METAI"] = pd.to_datetime(df["DATA"], errors="coerce").dt.year
                df['MOKĖTOJO ARBA GAVĖJO PAVADINIMAS'] = df['MOKĖTOJO ARBA GAVĖJO PAVADINIMAS'].fillna('Nenurodytas')
                df['SĄSKAITA'] = df['SĄSKAITA'].fillna('Sąskaita nenurodyta')
                df['MOKĖJIMO PASKIRTIS'] = df['MOKĖJIMO PASKIRTIS'].fillna('Be paskirties')
                df['SĄSKAITOS NR'] = df['SĄSKAITOS NR'].fillna('Sąskaita nenurodyta')

            else:
                return redirect(url_for('main.klaida'))

            if selection == 'old_seb':
                credit_df = df[df['Suma'] > 0].copy()
                debit_df = df[df['Suma'] < 0].copy()
                debit_df['Suma'] = debit_df['Suma'].abs()

                credit_pivot = credit_df.pivot_table(
                    index=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaita'],
                    columns='METAI', values='Suma', aggfunc='sum', fill_value=0).reset_index()

                debit_pivot = debit_df.pivot_table(
                    index=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaita'],
                    columns='METAI', values='Suma', aggfunc='sum', fill_value=0).reset_index()

                credit_reasons = credit_df.groupby(['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])[
                    'MOKĖJIMO PASKIRTIS'] \
                    .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

                debit_reasons = debit_df.groupby(['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])[
                    'MOKĖJIMO PASKIRTIS'] \
                    .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

                credit_final = pd.merge(credit_pivot, credit_reasons,
                                        on=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])
                debit_final = pd.merge(debit_pivot, debit_reasons, on=['Mokėtojas/Gavėjas', 'Mokėtojo/Gavėjo sąskaita'])

                credit_final = credit_final.rename(columns={
                    'Mokėtojas/Gavėjas': 'MOKĖTOJAS',
                    'Mokėtojo/Gavėjo sąskaita': 'MOKĖTOJO SĄSKAITA'
                })

                debit_final = debit_final.rename(columns={
                    'Mokėtojas/Gavėjas': 'GAVĖJAS',
                    'Mokėtojo/Gavėjo sąskaita': 'GAVĖJO SĄSKAITA'
                })

                all_years = sorted(df['METAI'].dropna().unique())
                all_years = [int(y) for y in all_years]

                credit_summary = credit_df.groupby('METAI')['Suma'].sum()
                debit_summary = debit_df.groupby('METAI')['Suma'].sum()

                credit_row = [credit_summary.get(year, 0) for year in all_years]
                debit_row = [debit_summary.get(year, 0) for year in all_years]

                credit_total = sum(credit_row)
                debit_total = sum(debit_row)

                credit_df_row = pd.DataFrame([credit_row + [credit_total]], columns=all_years + ['Viso'],
                                             index=['Bendros Pajamos'])
                debit_df_row = pd.DataFrame([debit_row + [debit_total]], columns=all_years + ['Viso'],
                                            index=['Bendros Išlaidos'])

                summary_combined = pd.concat([credit_df_row, debit_df_row])

            elif selection == 'new_seb':
                credit_df = df[df['DEBETAS/KREDITAS'] == 'C']

                credit_pivot = credit_df.pivot_table(
                    index=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'],
                    columns='METAI', values='SUMA', aggfunc='sum', fill_value=0).reset_index()

                credit_reasons = credit_df.groupby(['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])[
                    'MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

                credit_final = pd.merge(credit_pivot, credit_reasons,
                                        on=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])

                credit_final = credit_final.rename(columns={
                    'SĄSKAITOS NR': 'ASMENS SĄSKAITA',
                    'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS': 'MOKĖTOJAS',
                    'SĄSKAITA': 'MOKĖTOJO SĄSKAITA'
                })

                debit_df = df[df['DEBETAS/KREDITAS'] == 'D']

                debit_pivot = debit_df.pivot_table(
                    index=['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'],
                    columns='METAI', values='SUMA', aggfunc='sum', fill_value=0).reset_index()

                debit_reasons = debit_df.groupby(['SĄSKAITOS NR', 'MOKĖTOJO ARBA GAVĖJO PAVADINIMAS', 'SĄSKAITA'])[
                    'MOKĖJIMO PASKIRTIS'].apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

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

            else:
                return redirect(url_for('main.klaida'))

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Israsai_SEB.xlsx')
            with pd.ExcelWriter(result_path, engine='xlsxwriter') as writer:
                credit_final.to_excel(writer, sheet_name='Pajamos', index=False)
                debit_final.to_excel(writer, sheet_name='Išlaidos', index=False)
                summary_combined.reset_index().rename(columns={'index': ''}).to_excel(writer, sheet_name='Bendra', index=False)

            schedule_file_deletion(result_path, delay=60)

            session['last_file'] = result_path
            return redirect(url_for('main.sekmingai'))

        except Exception as e:
            print(f"Klaida: {e}")
            return redirect(url_for('main.klaida'))

    return redirect(url_for('main.klaida'))