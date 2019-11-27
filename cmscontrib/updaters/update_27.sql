begin;

alter table submissions add official boolean not null default 't';
alter table submissions alter official drop default;

alter table contests
    add analysis_enabled boolean not null default 'f',
    add analysis_start timestamp,
    add analysis_stop timestamp;
update contests set analysis_start = stop, analysis_stop = stop;
alter table contests
    alter analysis_enabled drop default,
    alter analysis_start set not null,
    alter analysis_stop set not null;

alter table contests
    drop constraint contests_check1,
    add constraint contests_check1 check (stop <= analysis_start),
    add constraint contests_check2 check (analysis_start <= analysis_stop),
    add constraint contests_check3 check (token_gen_initial <= token_gen_max);

rollback; -- change this to: commit;
