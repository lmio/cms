begin;

alter table printjobs
    add status_temp varchar[];
update printjobs
    set status_temp = array(select jsonb_array_elements_text(status::jsonb));
alter table printjobs
    alter status type varchar[] using status_temp,
    alter status set not null,
    drop status_temp;

rollback; -- change this to: commit;
