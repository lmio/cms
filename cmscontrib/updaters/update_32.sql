begin;

update datasets
    set time_limit = null
    where time_limit <= 0.0;
update datasets
    set memory_limit = null
    where memory_limit <= 0.0;

alter table datasets
    add constraint datasets_time_limit_check check (time_limit > 0),
    add constraint datasets_memory_limit_check check (memory_limit > 0);

rollback; -- change this to: commit;
