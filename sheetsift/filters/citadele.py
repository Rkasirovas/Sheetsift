import pandas as pd
import os
from flask import request, redirect, url_for, current_app, session

def analyze_citadele():
    file = request.files['file']
    if file and file.filename.endswith('.xlsx'):
        try:
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            df = pd.read_excel(filepath)

            columns = df.columns

            if 'Account Nr' in columns:
                df["METAI"] = pd.to_datetime(df["Date"], errors="coerce").dt.year
                df['ASMENS SĄSKAITA'] = df['Account Nr']
                df['MOKĖTOJAS/GAVĖJAS'] = df['Correspondent'].fillna('Nenurodytas')
                df['MOKĖJIMO PASKIRTIS'] = df['Details'].fillna('Be paskirties')
                df['PAJAMOS'] = df['Credit in transaction currency'].fillna(0)
                df['IŠLAIDOS'] = df['Debit in transaction currency'].fillna(0)

            elif 'IBAN' in columns:
                df["METAI"] = pd.to_datetime(df["OFS.DATE"].astype(str), format='%Y%m%d', errors='coerce').dt.year
                df['ASMENS SĄSKAITA'] = df['IBAN']
                df['MOKĖTOJAS/GAVĖJAS'] = df['OFS.CNP.NAME'].fillna('Nenurodytas')
                df['MOKĖJIMO PASKIRTIS'] = df['OFS.NARRATIVE'].fillna('Be paskirties')
                df['PAJAMOS'] = df.apply(lambda x: x['OFS.AMOUNT'] if x['SIGN'] == 'CR' else 0, axis=1)
                df['IŠLAIDOS'] = df.apply(lambda x: abs(x['OFS.AMOUNT']) if x['SIGN'] == 'DR' else 0, axis=1)

            # Kolkas neveikia
            # elif 'Data' in columns:
            #     df["METAI"] = pd.to_datetime(df["Data"], errors="coerce").dt.year
            #     df['ASMENS SĄSKAITA'] = 'Sąskaita nenurodyta'
            #     df['MOKĖTOJAS/GAVĖJAS'] = 'Mokėtojas/Gavėjas nenurodytas'
            #     df['MOKĖJIMO PASKIRTIS'] = df['Operacijos numeris ir paskirtis'].fillna('Be paskirties')
            #     df['CR'] = pd.to_numeric(df['CR'], errors='coerce').fillna(0)
            #     df['DR'] = pd.to_numeric(df['DR'], errors='coerce').fillna(0)
            #     df['PAJAMOS'] = df['CR'].apply(lambda x: x if x > 0 else 0)
            #     df['IŠLAIDOS'] = df['DR'].apply(lambda x: abs(x) if x != 0 else 0)
            #     df = df[(df['PAJAMOS'] > 0) | (df['IŠLAIDOS'] > 0)]

            else:
                return redirect(url_for('main.klaida'))

            credit_df = df[df['PAJAMOS'] > 0]
            credit_pivot = credit_df.pivot_table(
                index=['ASMENS SĄSKAITA', 'MOKĖTOJAS/GAVĖJAS'],
                columns='METAI', values='PAJAMOS', aggfunc='sum', fill_value=0).reset_index()

            credit_reasons = credit_df.groupby(['ASMENS SĄSKAITA', 'MOKĖTOJAS/GAVĖJAS'])['MOKĖJIMO PASKIRTIS'] \
                .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            credit_final = pd.merge(credit_pivot, credit_reasons, on=['ASMENS SĄSKAITA', 'MOKĖTOJAS/GAVĖJAS'])
            credit_final = credit_final.rename(columns={'MOKĖTOJAS/GAVĖJAS': 'MOKĖTOJAS'})

            debit_df = df[df['IŠLAIDOS'] > 0]
            debit_pivot = debit_df.pivot_table(
                index=['ASMENS SĄSKAITA', 'MOKĖTOJAS/GAVĖJAS'],
                columns='METAI', values='IŠLAIDOS', aggfunc='sum', fill_value=0).reset_index()

            debit_reasons = debit_df.groupby(['ASMENS SĄSKAITA', 'MOKĖTOJAS/GAVĖJAS'])['MOKĖJIMO PASKIRTIS'] \
                .apply(lambda x: ' ||\n'.join(sorted(set(x)))).reset_index()

            debit_final = pd.merge(debit_pivot, debit_reasons, on=['ASMENS SĄSKAITA', 'MOKĖTOJAS/GAVĖJAS'])
            debit_final = debit_final.rename(columns={'MOKĖTOJAS/GAVĖJAS': 'GAVĖJAS'})

            all_years = sorted(df['METAI'].dropna().unique())
            all_years = [int(y) for y in all_years]

            summary_list = []

            for account in df['ASMENS SĄSKAITA'].dropna().unique():
                account_credit = credit_df[credit_df['ASMENS SĄSKAITA'] == account]
                account_debit = debit_df[debit_df['ASMENS SĄSKAITA'] == account]

                credit_summary = account_credit.groupby('METAI')['PAJAMOS'].sum()
                debit_summary = account_debit.groupby('METAI')['IŠLAIDOS'].sum()

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

            result_path = os.path.join(current_app.config['RESULT_FOLDER'], 'Apdoroti_Išrasai_Citadele.xlsx')
            with pd.ExcelWriter(result_path, engine='xlsxwriter') as writer:
                credit_final.to_excel(writer, sheet_name='Pajamos', index=False)
                debit_final.to_excel(writer, sheet_name='Išlaidos', index=False)
                summary_combined.to_excel(writer, sheet_name='Bendra')

            session['last_file'] = result_path
            return redirect(url_for('main.sekmingai'))

        except Exception as e:
            print(f"Klaida: {e}")
            return redirect(url_for('main.klaida'))

    return redirect(url_for('main.klaida'))
