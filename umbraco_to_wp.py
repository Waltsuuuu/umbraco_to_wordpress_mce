import csv
import xml.etree.ElementTree as ET
import random
import string
from bs4 import BeautifulSoup

# Files for input and output
csv_file = "umbraco_users.csv"
output_sql = "wordpress_users.sql"

wp_users_table = "wp_users"
wp_usermeta_table = "wp_usermeta"

user_insert_template = """INSERT INTO {table} (user_login, user_pass, user_email, user_registered, user_activation_key) 
VALUES ('{username}', '', '{email}', NOW(), '{activation_key}');"""

meta_insert_template = """INSERT INTO {table} (user_id, meta_key, meta_value) 
VALUES ((SELECT ID FROM {user_table} WHERE user_login='{username}'), '{meta_key}', '{meta_value}');"""

delimiter = ","

# Generate a random string for activation key (simulating a password reset)
def generate_activation_key():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=20))

# Function to clean HTML content
def clean_html(content):
    if content:
        # Use BeautifulSoup to remove HTML tags
        return ''.join(BeautifulSoup(content, "html.parser").stripped_strings)
    return content

with open(csv_file, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file, delimiter=delimiter)
    headers = [h.strip() for h in reader.fieldnames]
    print("Detected CSV Headers:", headers)

required_columns = {"LoginName", "Email", "xml"}
if not required_columns.issubset(set(headers)):
    raise ValueError(f"Missing required columns! Found: {headers}")

sql_statements = []

with open(csv_file, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file, delimiter=delimiter)

    for row in reader:
        username = row.get("LoginName", "").strip()
        email = row.get("Email", "").strip()
        xml_data = row.get("xml", "").strip()

        if not username or not email:
            print(f"Skipping user with missing data: {row}")
            continue

        # Generate an activation key (this will prompt the user to reset their password)
        activation_key = generate_activation_key()

        # Insert user with no password (forcing a reset)
        sql_statements.append(user_insert_template.format(
            table=wp_users_table, username=username, email=email, activation_key=activation_key
        ))

        try:
            root = ET.fromstring(xml_data)
            metadata = {
                "phone_number": root.find("phone").text if root.find("phone") is not None else "",
                "company": root.find("company").text if root.find("company") is not None else "",
                "motorcycle": root.find("bike").text if root.find("bike") is not None else "",
                "custom_user_id": root.find("executorsNumber").text if root.find("executorsNumber") is not None else "",
                # Clean up the biographical information (remove HTML tags)
                "biographical_info": clean_html(root.find("profile").text) if root.find("profile") is not None else "",
                "fennoa_address": root.find("streetline1").text if root.find("streetline1") is not None else "",
                "fennoa_city": root.find("city").text if root.find("city") is not None else "",
                "fennoa_postcode": root.find("zipCode").text if root.find("zipCode") is not None else "",
                "fennoa_email": email,  # Using the email field for fennoa_email
            }

            for key, value in metadata.items():
                if value:
                    sql_statements.append(meta_insert_template.format(
                        table=wp_usermeta_table, user_table=wp_users_table, 
                        username=username, meta_key=key, meta_value=value
                    ))

        except ET.ParseError:
            print(f"Error parsing XML for user {username}, skipping metadata.")

with open(output_sql, "w", encoding="utf-8") as sql_file:
    sql_file.write("\n".join(sql_statements))

print(f"SQL file '{output_sql}' generated successfully!")
