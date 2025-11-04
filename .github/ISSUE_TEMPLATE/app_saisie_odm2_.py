
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.set_page_config(layout="wide")
st.title("💾 Application de Saisie ODM2 Étendue")

# Connexion à la base de données SQLite
conn = sqlite3.connect("odm2_agri.db")
cursor = conn.cursor()

# Fonction utilitaire pour insérer dans une table si n'existe pas déjà
def insert_if_not_exists(table, column, value):
    cursor.execute(f"INSERT OR IGNORE INTO {table} ({column}) VALUES (?)", (value,))
    conn.commit()

# 1. Formulaire : SamplingFeatures
with st.expander("🧪 Définir un échantillon (SamplingFeatures)"):
    sample_name = st.text_input("Nom de l'échantillon")
    sample_type = st.selectbox("Type d'échantillon", ["Soil", "Plant", "Larva", "Fungus", "Gas"])
    location_name = st.text_input("Lieu")
    latitude = st.number_input("Latitude", format="%.6f")
    longitude = st.number_input("Longitude", format="%.6f")
    if st.button("Ajouter l'échantillon"):
        insert_if_not_exists("CV_SampleType", "sample_type", sample_type)
        cursor.execute(
            "INSERT INTO SamplingFeatures (sample_name, sample_type, location_name, latitude, longitude) VALUES (?, ?, ?, ?, ?)",
            (sample_name, sample_type, location_name, latitude, longitude)
        )
        conn.commit()
        st.success("✅ Échantillon ajouté avec succès.")

# 2. Formulaire : Méthode
with st.expander("🔬 Définir une méthode de mesure"):
    method_name = st.text_input("Nom de la méthode")
    description = st.text_area("Description")
    tool_used = st.text_input("Outil utilisé")
    method_type = st.selectbox("Type de méthode", ["FieldMeasurement", "Laboratory", "Modeling", "StatisticalAnalysis", "RemoteSensing"])
    if st.button("Supprimer la méthode", key="btn_delete_method") and confirm_meth:
        cursor.execute("DELETE FROM Methods WHERE method_id = ?", (method_id_to_delete,))
        conn.commit()
        st.success(f"✅ Méthode {method_id_to_delete} supprimée avec succès.")
    elif st.button("Supprimer la méthode", key="btn_warn_method"):
        st.warning("⚠️ Vous devez confirmer la suppression en cochant la case.")

# 3. Formulaire : Variable
with st.expander("📊 Définir une variable mesurée"):
    variable_name = st.text_input("Nom de la variable")
    variable_category = st.selectbox("Catégorie", ["Chemical", "Biological", "Environmental", "Agronomic"])
    if st.button("Supprimer l’action", key="btn_delete_action") and confirm_act:
        cursor.execute("DELETE FROM Actions WHERE action_id = ?", (action_id_to_delete,))
        conn.commit()
        st.success(f"✅ Action {action_id_to_delete} supprimée avec succès.")
    elif st.button("Supprimer l’action", key="btn_warn_action"):
        st.warning("⚠️ Vous devez confirmer la suppression en cochant la case.")

# 4. Formulaire : Unité
with st.expander("📐 Définir une unité"):
    unit_name = st.text_input("Nom de l’unité")
    unit_symbol = st.text_input("Symbole")
    definition = st.text_input("Définition")
    if st.button("Ajouter l’unité"):
        insert_if_not_exists("CV_Unit", "unit_name", unit_name)
        cursor.execute(
            "INSERT INTO Units (unit_name) VALUES (?)", (unit_name,)
        )
        cursor.execute(
            "INSERT OR IGNORE INTO CV_Unit (unit_name, unit_symbol, definition) VALUES (?, ?, ?)",
            (unit_name, unit_symbol, definition)
        )
        conn.commit()
        st.success("✅ Unité ajoutée.")

# 5. Formulaire : Attribut contextuel
with st.expander("🌿 Ajouter un attribut contextuel"):
    samplingfeature_id = st.number_input("ID de l’échantillon concerné", step=1)
    attribute_name = st.text_input("Nom de l’attribut contextuel (ex: mushroom_species)")
    attribute_value = st.text_input("Valeur")
    source = st.text_input("Source")
    notes = st.text_area("Notes")
    if st.button("Ajouter l’attribut contextuel"):
        insert_if_not_exists("CV_ContextualAttribute", "attribute_name", attribute_name)
        cursor.execute(
            "INSERT INTO ContextualAttributes (samplingfeature_id, attribute_name, attribute_value, source, notes) VALUES (?, ?, ?, ?, ?)",
            (samplingfeature_id, attribute_name, attribute_value, source, notes)
        )
        conn.commit()
        st.success("✅ Attribut ajouté.")

# 6. Affichage des données
with st.expander("📄 Afficher les échantillons enregistrés"):
    df = pd.read_sql_query("SELECT * FROM SamplingFeatures", conn)
    st.dataframe(df)

conn.close()


# 6. Formulaire : Action + FeatureAction
with st.expander("⚙️ Enregistrer une action sur un échantillon"):
    fa_samplingfeature_id = st.number_input("ID de l’échantillon (SamplingFeature)", step=1, key="fa_sf")
    sampling_date = st.date_input("Date de l’action")
    sampling_depth = st.number_input("Profondeur d’échantillonnage (en cm)", value=0.0, step=0.1)
    additional_notes = st.text_area("Notes supplémentaires")
    action_type = st.selectbox("Type d’action", ["Sampling", "Extraction", "Measurement", "Cultivation", "Sequencing"], key="act_type")
    method_id = st.number_input("ID de la méthode associée", step=1, key="meth_id")
    if st.button("Enregistrer l'action"):
        insert_if_not_exists("CV_ActionType", "action_type", action_type)
        cursor.execute(
            "INSERT INTO FeatureActions (samplingfeature_id, sampling_date, sampling_depth, additional_notes) VALUES (?, ?, ?, ?)",
            (fa_samplingfeature_id, sampling_date, sampling_depth, additional_notes)
        )
        fa_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Actions (featureaction_id, action_type, method_id) VALUES (?, ?, ?)",
            (fa_id, action_type, method_id)
        )
        conn.commit()
        st.success(f"✅ Action enregistrée pour l’échantillon {fa_samplingfeature_id}.")

# 7. Formulaire : Résultat + ResultValue
with st.expander("📈 Enregistrer un résultat de mesure"):
    result_featureaction_id = st.number_input("ID de FeatureAction", step=1)
    result_type = st.selectbox("Type de résultat", ["Concentration", "Index", "Count", "Binary"])
    variable_id = st.number_input("ID de la variable", step=1)
    unit_id = st.number_input("ID de l’unité", step=1)
    date_part = st.date_input("Date de la mesure", value=datetime.now().date())
    time_part = st.time_input("Heure de la mesure", value=datetime.now().time())
    timestamp = datetime.combine(date_part, time_part)
    value = st.number_input("Valeur mesurée", step=0.1)
    if st.button("Ajouter le résultat"):
        insert_if_not_exists("CV_ResultType", "result_type", result_type)
        cursor.execute(
            "INSERT INTO Results (featureaction_id, result_type, variable_id, unit_id) VALUES (?, ?, ?, ?)",
            (result_featureaction_id, result_type, variable_id, unit_id)
        )
        result_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO ResultValues (result_id, timestamp, value) VALUES (?, ?, ?)",
            (result_id, timestamp, value)
        )
        conn.commit()
        st.success("✅ Résultat enregistré avec succès.")


# 8. 🔎 Recherche et modification des enregistrements
with st.expander("🔎 Rechercher / Modifier un échantillon"):
    search_id = st.number_input("ID de l’échantillon à rechercher", step=1, key="search_id")
    if st.button("Rechercher l’échantillon"):
        df_sf = pd.read_sql_query("SELECT * FROM SamplingFeatures WHERE samplingfeature_id = ?", conn, params=(search_id,))
        if df_sf.empty:
            st.warning("❌ Aucun échantillon trouvé avec cet ID.")
        else:
            st.dataframe(df_sf)

            with st.form(key="edit_sample_form"):
                new_name = st.text_input("Nouveau nom", df_sf.loc[0, "sample_name"])
                new_type = st.text_input("Nouveau type", df_sf.loc[0, "sample_type"])
                new_location = st.text_input("Nouveau lieu", df_sf.loc[0, "location_name"])
                new_lat = st.number_input("Nouvelle latitude", value=df_sf.loc[0, "latitude"])
                new_lon = st.number_input("Nouvelle longitude", value=df_sf.loc[0, "longitude"])
                submit = st.form_submit_button("✅ Enregistrer les modifications")
                if submit:
                    cursor.execute(
                        "UPDATE SamplingFeatures SET sample_name = ?, sample_type = ?, location_name = ?, latitude = ?, longitude = ? WHERE samplingfeature_id = ?",
                        (new_name, new_type, new_location, new_lat, new_lon, search_id)
                    )
                    conn.commit()
                    st.success("✅ Échantillon mis à jour avec succès.")


# 9. ✏️ Rechercher / Modifier un résultat
with st.expander("✏️ Rechercher / Modifier un résultat"):
    result_id_search = st.number_input("ID du résultat à modifier", step=1, key="result_edit_id")
    if st.button("Rechercher le résultat"):
        df_res = pd.read_sql_query("SELECT * FROM Results WHERE result_id = ?", conn, params=(result_id_search,))
        df_val = pd.read_sql_query("SELECT * FROM ResultValues WHERE result_id = ?", conn, params=(result_id_search,))
        if df_res.empty:
            st.warning("❌ Aucun résultat trouvé.")
        else:
            st.subheader("Résultat actuel")
            st.dataframe(df_res)
            st.dataframe(df_val)

            with st.form(key="edit_result_form"):
                new_result_type = st.text_input("Type de résultat", df_res.loc[0, "result_type"])
                new_variable_id = st.number_input("ID variable", value=df_res.loc[0, "variable_id"])
                new_unit_id = st.number_input("ID unité", value=df_res.loc[0, "unit_id"])
                new_timestamp = st.text_input("Horodatage (YYYY-MM-DD HH:MM:SS)", df_val.loc[0, "timestamp"])
                new_value = st.number_input("Nouvelle valeur", value=df_val.loc[0, "value"])
                submit_edit = st.form_submit_button("✅ Mettre à jour")
                if submit_edit:
                    cursor.execute(
                        "UPDATE Results SET result_type = ?, variable_id = ?, unit_id = ? WHERE result_id = ?",
                        (new_result_type, new_variable_id, new_unit_id, result_id_search)
                    )
                    cursor.execute(
                        "UPDATE ResultValues SET timestamp = ?, value = ? WHERE result_id = ?",
                        (new_timestamp, new_value, result_id_search)
                    )
                    conn.commit()
                    st.success("✅ Résultat mis à jour avec succès.")


# 10. ❌ Supprimer un enregistrement
with st.expander("❌ Supprimer un échantillon ou un résultat"):
    del_option = st.radio("Que voulez-vous supprimer ?", ["Échantillon", "Résultat"])
    if del_option == "Échantillon":
        del_sample_id = st.number_input("ID de l’échantillon à supprimer", step=1, key="del_sample_id")
        if st.button("Supprimer l’échantillon"):
            cursor.execute("DELETE FROM ContextualAttributes WHERE samplingfeature_id = ?", (del_sample_id,))
            cursor.execute("DELETE FROM Annotations WHERE samplingfeature_id = ?", (del_sample_id,))
            cursor.execute("DELETE FROM FeatureActions WHERE samplingfeature_id = ?", (del_sample_id,))
            cursor.execute("DELETE FROM SamplingFeatures WHERE samplingfeature_id = ?", (del_sample_id,))
            conn.commit()
            st.success(f"✅ Échantillon {del_sample_id} supprimé avec succès.")
    else:
        del_result_id = st.number_input("ID du résultat à supprimer", step=1, key="del_result_id")
        if st.button("Supprimer le résultat"):
            cursor.execute("DELETE FROM ResultValues WHERE result_id = ?", (del_result_id,))
            cursor.execute("DELETE FROM Results WHERE result_id = ?", (del_result_id,))
            conn.commit()
            st.success(f"✅ Résultat {del_result_id} supprimé avec succès.")


# 11. ❌ Supprimer une méthode ou une action
with st.expander("🧨 Supprimer une méthode ou une action spécifique"):
    del_entity = st.radio("Que voulez-vous supprimer ?", ["Méthode", "Action"])

    if del_entity == "Méthode":
        method_id_to_delete = st.number_input("ID de la méthode à supprimer", step=1, key="delete_method_id")
        confirm_meth = st.checkbox("Confirmer la suppression de cette méthode")
        if st.button("Supprimer la méthode") and confirm_meth:
            cursor.execute("DELETE FROM Methods WHERE method_id = ?", (method_id_to_delete,))
            conn.commit()
            st.success(f"✅ Méthode {method_id_to_delete} supprimée avec succès.")
        elif st.button("Supprimer la méthode"):
            st.warning("⚠️ Vous devez confirmer la suppression en cochant la case.")

    elif del_entity == "Action":
        action_id_to_delete = st.number_input("ID de l’action à supprimer", step=1, key="delete_action_id")
        confirm_act = st.checkbox("Confirmer la suppression de cette action")
        if st.button("Supprimer l’action") and confirm_act:
            cursor.execute("DELETE FROM Actions WHERE action_id = ?", (action_id_to_delete,))
            conn.commit()
            st.success(f"✅ Action {action_id_to_delete} supprimée avec succès.")
        elif st.button("Supprimer l’action"):
            st.warning("⚠️ Vous devez confirmer la suppression en cochant la case.")


# 12. 📊 Visualisation complète des données
with st.expander("📊 Visualiser toutes les données stockées"):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "SamplingFeatures", "FeatureActions", "Actions",
        "Methods", "Variables", "Results", "ContextualAttributes"
    ])

    with tab1:
        st.subheader("🧪 Sampling Features")
        df_sf = pd.read_sql_query("SELECT * FROM SamplingFeatures", conn)
        st.dataframe(df_sf)

    with tab2:
        st.subheader("📅 Feature Actions")
        df_fa = pd.read_sql_query("SELECT * FROM FeatureActions", conn)
        st.dataframe(df_fa)

    with tab3:
        st.subheader("⚙️ Actions")
        df_act = pd.read_sql_query("SELECT * FROM Actions", conn)
        st.dataframe(df_act)

    with tab4:
        st.subheader("🧰 Méthodes")
        df_methods = pd.read_sql_query("SELECT * FROM Methods", conn)
        st.dataframe(df_methods)

    with tab5:
        st.subheader("📐 Variables et Unités")
        df_var = pd.read_sql_query("SELECT * FROM Variables", conn)
        df_unit = pd.read_sql_query("SELECT * FROM Units", conn)
        st.dataframe(df_var)
        st.dataframe(df_unit)

    with tab6:
        st.subheader("📈 Résultats")
        df_res = pd.read_sql_query("SELECT * FROM Results", conn)
        df_val = pd.read_sql_query("SELECT * FROM ResultValues", conn)
        st.dataframe(df_res)
        st.dataframe(df_val)

    with tab7:
        st.subheader("🧩 Attributs contextuels")
        df_ctx = pd.read_sql_query("SELECT * FROM ContextualAttributes", conn)
        st.dataframe(df_ctx)


# Boutons d'export CSV pour chaque table
def export_button(df, name):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label=f"⬇️ Télécharger {name}.csv",
        data=csv,
        file_name=f"{name}.csv",
        mime='text/csv'
    )

# 13. 📦 Ajout des exports CSV
with st.expander("📤 Exporter les données"):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "SamplingFeatures", "FeatureActions", "Actions",
        "Methods", "Variables & Units", "Results", "ContextualAttributes"
    ])

    with tab1:
        df = pd.read_sql_query("SELECT * FROM SamplingFeatures", conn)
        st.dataframe(df)
        export_button(df, "SamplingFeatures")

    with tab2:
        df = pd.read_sql_query("SELECT * FROM FeatureActions", conn)
        st.dataframe(df)
        export_button(df, "FeatureActions")

    with tab3:
        df = pd.read_sql_query("SELECT * FROM Actions", conn)
        st.dataframe(df)
        export_button(df, "Actions")

    with tab4:
        df = pd.read_sql_query("SELECT * FROM Methods", conn)
        st.dataframe(df)
        export_button(df, "Methods")

    with tab5:
        df1 = pd.read_sql_query("SELECT * FROM Variables", conn)
        df2 = pd.read_sql_query("SELECT * FROM Units", conn)
        st.dataframe(df1)
        export_button(df1, "Variables")
        st.dataframe(df2)
        export_button(df2, "Units")

    with tab6:
        df1 = pd.read_sql_query("SELECT * FROM Results", conn)
        df2 = pd.read_sql_query("SELECT * FROM ResultValues", conn)
        st.dataframe(df1)
        export_button(df1, "Results")
        st.dataframe(df2)
        export_button(df2, "ResultValues")

    with tab7:
        df = pd.read_sql_query("SELECT * FROM ContextualAttributes", conn)
        st.dataframe(df)
        export_button(df, "ContextualAttributes")
