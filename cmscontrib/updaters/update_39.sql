begin;

alter table questions add admin_id integer;
create index ix_questions_admin_id on questions using btree (admin_id);
alter table questions add foreign key (admin_id) references admins(id) on update cascade on delete set null;

alter table announcements add admin_id integer;
create index ix_announcements_admin_id on announcements using btree (admin_id);
alter table announcements add foreign key (admin_id) references admins(id) on update cascade on delete set null;

alter table messages add admin_id integer;
create index ix_messages_admin_id on messages using btree (admin_id);
alter table messages add foreign key (admin_id) references admins(id) on update cascade on delete set null;

rollback; -- change this to: commit;
