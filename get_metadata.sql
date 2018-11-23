-- все таблицы
select 
	t.object_id,
	s.name as schema,
	t.name as name,
	t.modify_date as last_update
from 
	sys.tables t
	join sys.schemas s on t.schema_id = s.schema_id

-- все синонимы
select 
	sn.object_id,
	s.name as schema_name,
	o.name as object_name,
	o.type,
	o.modify_date,
	OBJECT_ID(sn.base_object_name) as original_id
from 
	sys.synonyms sn
	join sys.objects o on o.object_id = sn.object_id
	join sys.schemas s on o.schema_id = s.schema_id
where OBJECT_ID(sn.base_object_name) is not null

-- все триггеры
select 
	m.object_id,
	s.name as schema_name,
	o.name as object_name,
	o.type,
	o.modify_date,
	o.parent_object_id as table_id,
	m.definition
from 
	sys.sql_modules m
	join sys.objects o on o.object_id = m.object_id
	join sys.schemas s on o.schema_id = s.schema_id
where 
o.type = 'TR'
-- and o.parent_object_id = @table_id -- все триггеры определённой таблицы

-- все процедуры
select 
	m.object_id,
	s.name as schema_name,
	o.name as object_name,
	o.type,
	o.modify_date,
	m.definition
from 
	sys.sql_modules m
	join sys.objects o on o.object_id = m.object_id
	join sys.schemas s on o.schema_id = s.schema_id
where o.type = 'P'

-- все представления
select 
	m.object_id,
	s.name as schema_name,
	o.name as object_name,
	o.type,
	o.modify_date,
	m.definition
from 
	sys.sql_modules m 
	join sys.objects o on o.object_id = m.object_id
	join sys.schemas s on o.schema_id = s.schema_id
where o.type = 'V'

-- все функции
select 
	m.object_id,
	s.name as schema_name,
	o.name as object_name,
	o.type,
	o.modify_date,
	m.definition
from 
	sys.sql_modules m 
	join sys.objects o on o.object_id = m.object_id
	join sys.schemas s on o.schema_id = s.schema_id
where o.type in ('TF', 'FN')

-- вообще всё (и даже больше)
select * from(
	select 
		s.name as schema_name, 
		o.name as object_name, 
		o.object_id, o.schema_id, 
		o.type, 
		o.create_date, 
		o.modify_date, 
		m.definition, 
		sn.base_object_name, 
		OBJECT_ID(sn.base_object_name) as base_object_id,
		t.parent_id as triggered_table_id
	from sys.objects o
	join sys.schemas s on s.schema_id = o.schema_id
	left join sys.sql_modules m on o.object_id = m.object_id
	left join sys.synonyms sn on sn.object_id = o.object_id
	left join sys.triggers t on t.object_id = o.object_id
	where 
		s.principal_id = 1 and
		o.type in ('C', 'D', 'F', 'FN', 'P', 'PK', 'SN', 'U', 'V', 'TR', 'TF') and
		sn.base_object_name is null or OBJECT_ID(sn.base_object_name) is not null
) main
where
(base_object_id is not null and base_object_name is not null) or base_object_name is null
ORDER BY type