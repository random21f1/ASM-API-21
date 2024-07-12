from flask import Flask, request, jsonify
import pyodbc
import xml.etree.ElementTree as ET

app = Flask(__name__)

def create_connection():
    conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=host.docker.internal;DATABASE=testasm;UID=Sam;PWD=admin;Encrypt=No;')
    return conn

@app.route('/test-ams-optimisation', methods=['GET', 'POST'])
def test():
    if request.method == 'GET':
        return jsonify({"message": "Hello World"})
    data = request.json
    return jsonify(data)

@app.route('/', methods=['GET', 'POST'])
def test2():
    if request.method == 'GET':
        return jsonify({"message": "Hello World from Home"})
    data = request.json
    return jsonify(data)

@app.route('/get-ams-optimisation', methods=['POST'])
def get_ams_optimisation():
    try:
        data = request.json

        if data.get('password') != "dom-55*2=110":
            return jsonify({"message": "Authentication filed!! Enter correct password"}), 401
        
        conn = create_connection()
        cursor = conn.cursor()

        profile_id = data.get('ProfileId')
        max_unknown_relevance_terms = data.get('MaxUnknownRelevanceTerms', 100)
        days_adjust_factor = data.get('DaysAdjustFactor', 1.00)

        # Convert JSON to XML
        targeting_xml = ET.Element('TargetingOptimisationDetail')
        for item in data.get('TargetingOptimisationDetail', []):
            detail = ET.SubElement(targeting_xml, 'Detail')
            for key, value in item.items():
                ET.SubElement(detail, key).text = str(value)

        search_term_xml = ET.Element('AMSSearchTermOptimisationDetail')
        for item in data.get('AMSSearchTermOptimisationDetail', []):
            detail = ET.SubElement(search_term_xml, 'Detail')
            for key, value in item.items():
                ET.SubElement(detail, key).text = str(value)

        previous_targeting_xml = ET.Element('PreviousTargetingOptimisationDetail')
        for item in data.get('PreviousTargetingOptimisationDetail', []):
            detail = ET.SubElement(previous_targeting_xml, 'Detail')
            for key, value in item.items():
                ET.SubElement(detail, key).text = str(value)


        sql = """
                DECLARE @ReturnValue NVARCHAR(4000);
                EXEC sp_GetAMSOptimisation2 
                    @ProfileId=?, 
                    @MaxUnkwonRelevanceTerms=?, 
                    @DaysAdjustFactor=?, 
                    @TargetingOptimisationDetail=?, 
                    @AMSSearchTermOptimisationDetail=?, 
                    @PreviousTargetingOptimisationDetail=?,
                    @ReturnValue=@ReturnValue OUTPUT;
                SELECT @ReturnValue AS ReturnValue;
            """

        params = (
            profile_id,
            max_unknown_relevance_terms,
            days_adjust_factor,
            ET.tostring(targeting_xml).decode(),
            ET.tostring(search_term_xml).decode(),
            ET.tostring(previous_targeting_xml).decode()
        )
        
        # Execute the SQL command
        cursor.execute(sql, params)

        # Execute stored procedure
        # params = ( profile_id, max_unknown_relevance_terms, days_adjust_factor, ET.tostring(targeting_xml).decode(), ET.tostring(search_term_xml).decode(), ET.tostring(previous_targeting_xml).decode())
        # cursor.execute("{CALL sp_GetAMSOptimisation2(?,?,?,?,?,?,?)}", params)

        # Fetch results
        targeting_results = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        cursor.nextset()
        search_term_results = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        cursor.nextset()
        summary_results = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]
        cursor.nextset()

        # Fetch the @ReturnValue
        return_value = cursor.fetchone()[0]
        # Check if @ReturnValue is not empty
        if return_value != "":
            return jsonify({"error": return_value}), 500

        cursor.close()
        conn.close()

        return jsonify({
            'TargetingOptimisationDetail': targeting_results,
            'AMSSearchTermOptimisationDetail': search_term_results,
            'Summary': summary_results
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
