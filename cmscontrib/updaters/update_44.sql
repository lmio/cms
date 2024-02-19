begin;

update executables set filename = filename || '.exe' where submission_id in (select id from submissions where language = 'C# / Mono');
update executables set filename = filename || '.jar' where submission_id in (select id from submissions where language = 'Java / JDK');
update executables set filename = filename || '.php' where submission_id in (select id from submissions where language = 'PHP');
update executables set filename = filename || '.zip' where submission_id in (select id from submissions where language = 'Python 2 / CPython');
update executables set filename = filename || '.pyz' where submission_id in (select id from submissions where language = 'Python 3 / CPython');

rollback; -- change this to: commit;
