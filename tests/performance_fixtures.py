"""Complete synthetic classifier rows; missing fields must be tested explicitly."""
def performance_row(**values):
 row=dict.fromkeys(('music','singing','choir_singing','speech','rapping','laughter','baby_laughter','belly_laugh','crying_sobbing','sigh','breathing','gasp','screaming','shout','yell'),0.)
 row.update(start=0.,duration=1.)
 row.update(values)
 return row
