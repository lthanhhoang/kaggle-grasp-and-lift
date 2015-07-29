import pandas as pd
import argparse
from subprocess import call

parser = argparse.ArgumentParser(description='Filter out 0 labels from the training set')
parser.add_argument('-n', default=-1, type=int, help='how many files to filter', dest='num_files')
parser.add_argument('-c', default=False, action='store_true', help='clear filtered file directory', dest='should_rm')
args = parser.parse_args()

if args.should_rm:
    print 'removing old files'
    call(['rm', '-rf', 'data/filtered'])
    call(['mkdir', 'data/filtered'])
    print 'done'

data_in_path = "data/train/subj{0}_series{1}_data.csv"
events_in_path = "data/train/subj{0}_series{1}_events.csv"
data_out_path = "data/filtered/subj{0}_series{1}_data.csv"
events_out_path = "data/filtered/subj{0}_series{1}_events.csv"
num_subjects = 12
num_series = 8
offset = 0

total_samples = 0
total_used_samples = 0
# we want inclusive ranges
for subj in xrange(1, num_subjects + 1):
    for series in xrange(1, num_series + 1):
        # load files
        print 'reading files for subject {}, series {}'.format(subj, series)
        data_df = pd.read_csv(data_in_path.format(subj, series))
        events_df = pd.read_csv(events_in_path.format(subj, series))

        # tidy up the indexes
        data_df['id'] = data_df['id'].map(lambda x: int(x.split('_')[2]))
        events_df['id'] = events_df['id'].map(lambda x: int(x.split('_')[2]))

        # find event indices
        print 'filtering events'
        start_df = events_df[events_df['HandStart'] != 0].id
        end_df = events_df[events_df['BothReleased'] != 0].id
        num_events = start_df.count() / 150
        assert start_df.count() == end_df.count()

        print 'found: ' + str(num_events) + ' events'

        # event_boundaries is a list of pairs (t_start, t_end)
        event_boundaries = []
        for i in xrange(0, num_events * 150, 150):
            # make sure that we're not doing it wrong
            # i should be an index of an particular event's start and end
            if i > 0:
                assert start_df.iloc[i] - start_df.iloc[i - 1] > 1
                assert end_df.iloc[i] - end_df.iloc[i - 1] > 1
            assert start_df.iloc[i] < end_df.iloc[i]
            event_boundaries.append((start_df.iloc[i] - offset, end_df.iloc[i] + offset))

        # print some information
        event_lengths = map(lambda (s, e): e - s + 1, event_boundaries)
        used_samples = reduce(lambda x, y: x + y, event_lengths)
        avg_length = used_samples / num_events
        percent_used = float(used_samples) / events_df['id'].count() * 100
        total_samples += events_df['id'].count()
        total_used_samples += used_samples
        print 'using {} samples ({:.2f}%)'.format(used_samples, percent_used)
        print 'average event length: {}'.format(avg_length)
        sparsity = 1 - (150. * 6.) / avg_length
        print 'sparsity: {}'.format(sparsity)

        # extract only selected ranges
        data_slices = []
        events_slices = []
        assert len(event_boundaries) == num_events
        for i in xrange(0, num_events):
            start, end = event_boundaries[i]
            data_slices.append(data_df.iloc[start:end+1])
            events_slices.append(events_df.iloc[start:end+1])

        # concat and save the slices
        pd.concat(data_slices).to_csv(data_out_path.format(subj, series), index=False)
        pd.concat(events_slices).to_csv(events_out_path.format(subj, series), index=False)

        print 'done'

        if args.num_files > -1 and ((subj - 1) * num_series) + series >= args.num_files:
            quit()

total_percent_used = float(total_used_samples) / total_samples * 100
print 'used {} samples ({:.2f}%)'.format(total_used_samples, total_percent_used)
