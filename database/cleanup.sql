--- DRop Tables 
------------------------------------------------
drop table fleets if exists cascade;
drop table subscription_plans if exists cascade;       
drop table subscription_plans if exists cascade;
drop table vehicles if exists cascade;
drop table trips if exists cascade;
drop table expenses if exists cascade;
drop table fuel_benchmarks if exists cascade;
drop table users if exists cascade;




-- ----------------------------------------------------------------------------
-- VahanKhata Demo Data Cleanup
truncate table fleets cascade;
truncate table subscription_plans cascade;
truncate table vehicles cascade;
truncate table trips cascade;
truncate table expenses cascade;
truncate table fuel_benchmarks cascade;
truncate table users cascade;