begin;

update datasets
    set memory_limit = memory_limit * 1024 * 1024;

alter table datasets
    add constraint datasets_memory_limit_check1 check (MOD(memory_limit, 1048576) = 0);

rollback; -- change this to: commit;
