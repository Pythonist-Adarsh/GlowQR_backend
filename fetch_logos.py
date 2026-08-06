import psycopg2
conn = psycopg2.connect('postgresql://postgres.bujkgobjfclkoqvvzrfk:Adarsh%40Pgadmin%40123@aws-1-ap-northeast-2.pooler.supabase.com:6543/postgres?sslmode=require')
c = conn.cursor()
c.execute("SELECT name, logo_url FROM businesses WHERE name ILIKE '%DANBAM%' OR name ILIKE '%Aadayein%' OR name ILIKE '%Adayein%' OR name ILIKE '%Taxcare%' OR name ILIKE '%Vernika%';")
print(c.fetchall())
