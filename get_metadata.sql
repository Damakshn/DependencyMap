select * from(
select s.name as schema_name, o.name as object_name, o.object_id, o.schema_id, o.type, o.create_date, o.modify_date, m.definition, sn.base_object_name, OBJECT_ID(sn.base_object_name) as base_object_id 
from sys.objects o
join sys.schemas s on s.schema_id = o.schema_id
left join sys.sql_modules m on o.object_id = m.object_id
left join sys.synonyms sn on sn.object_id = o.object_id
where 
s.principal_id = 1 and
o.type in ('C', 'D', 'F', 'FN', 'P', 'PK', 'SN', 'U', 'V')) main
where
(base_object_id is not null and base_object_name is not null) or base_object_name is null
ORDER BY type