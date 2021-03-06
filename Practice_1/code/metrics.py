import numpy
from sklearn.linear_model import LinearRegression

__author__ = 'mikhail91'


class HitsMatchingEfficiency(object):
    def __init__(self, eff_threshold=0.5):
        """
        This class calculates tracks efficiencies, reconstruction efficiency, ghost rate and clone rate
         for one event using hits matching approach.

        :param eff_threshold: float, threshold value of a track efficiency to consider a track as a reconstructed one.
        """

        self.eff_threshold = eff_threshold

    def fit(self, event, labels):
        """
        The method calculates all metrics.
        :param event: pandas.DataFrame, true event, with column "TrackId"
        :param labels: numpy.array, recognized labels of the hits.
        """

        true_labels = event.TrackID.values
        unique_labels = numpy.unique(labels)

        # Calculate efficiencies
        efficiencies = []
        tracks_id = []

        for label in unique_labels:
            if label != -1:
                track = true_labels[labels == label]
                # if len(track[track != -1]) == 0:
                #    continue
                unique, counts = numpy.unique(track, return_counts=True)

                eff = 1. * counts.max() / len(track)
                efficiencies.append(eff)

                tracks_id.append(unique[counts == counts.max()][0])

        tracks_id = numpy.array(tracks_id)
        efficiencies = numpy.array(efficiencies)
        self.efficiencies_ = efficiencies

        # Calculate avg. efficiency
        avg_efficiency = efficiencies.mean()
        self.avg_efficiency_ = avg_efficiency

        # Calculate reconstruction efficiency
        true_tracks_id = numpy.unique(event.TrackID.values)
        n_tracks = (true_tracks_id != -1).sum()

        reco_tracks_id = tracks_id[efficiencies >= self.eff_threshold]
        unique, counts = numpy.unique(reco_tracks_id[reco_tracks_id != -1], return_counts=True)

        if n_tracks > 0:
            reconstruction_efficiency = 1. * len(unique) / (n_tracks)
            self.reconstruction_efficiency_ = reconstruction_efficiency
        else:
            self.reconstruction_efficiency_ = 0

        # Calculate ghost rate
        if n_tracks > 0:
            ghost_rate = 1. * (len(tracks_id) - len(reco_tracks_id[reco_tracks_id != -1])) / (n_tracks)
            self.ghost_rate_ = ghost_rate
        else:
            self.ghost_rate_ = 0

        # Calculate clone rate
        reco_tracks_id = tracks_id[efficiencies >= self.eff_threshold]
        unique, counts = numpy.unique(reco_tracks_id[reco_tracks_id != -1], return_counts=True)

        if n_tracks > 0:
            clone_rate = (counts - numpy.ones(len(counts))).sum() / (n_tracks)
            self.clone_rate_ = clone_rate
        else:
            self.clone_rate_ = 0



class ParameterMatchingEfficiency(object):
    def __init__(self, delta_k, delta_b):
        """
        This class calculates tracks efficiencies, reconstruction efficiency, ghost rate and clone rate
         for one event using parameters matching.
        :param delta_k: float, maximum abs difference between a true track k value and a recognized one
            to consider the track to be reconstructed.
        :param delta_b: float, maximum abs difference between a true track b value and a recognized one
            to consider the track to be reconstructed.
        """
        self.delta_k = delta_k
        self.delta_b = delta_b

    def fit(self, event, labels):
        """
        The method calculates all metrics
        .
        :param event: pandas.DataFrame, true event.
        :param labels: numpy.array, recognized labels of the hits.
        """

        true_labels = event.TrackID.values
        unique_true_labels = numpy.unique(true_labels)
        unique_labels = numpy.unique(labels)

        # N tracks
        true_tracks_id = numpy.unique(event.TrackID.values)
        n_tracks = (true_tracks_id != -1).sum()

        # Calculate parameters of the true tracks
        true_params = []
        for label in unique_true_labels:
            if label != -1:
                true_track = event[event.TrackID == label]
                X = true_track.X.values.reshape(-1, 1)
                y = true_track.y.values

                lr = LinearRegression()
                lr.fit(X, y)

                true_params += [(lr.coef_[0], lr.intercept_)]

        true_params = numpy.array(true_params)

        # Calculate parameters of the recognized tracks
        params = []
        for label in unique_labels:
            if label != -1:
                track = event[labels == label]
                X = track.X.values.reshape(-1, 1)
                y = track.y.values

                lr = LinearRegression()
                lr.fit(X, y)

                params += [(lr.coef_[0], lr.intercept_)]

        params = numpy.array(params)

        # Calculate reconstructions, ghosts and clones
        n_reconstructions = 0
        n_ghosts = 0

        true_used = numpy.zeros(len(true_params))
        used = numpy.zeros(len(params))
        for id, one_param in enumerate(params):
            n_matchings = 0

            for true_id, one_true_param in enumerate(true_params):
                if (abs(one_true_param[0] - one_param[0]) <= self.delta_k) & \
                        (abs(one_true_param[1] - one_param[1]) <= self.delta_b):

                    n_matchings += 1
                    if true_used[true_id] == 0 and used[id] == 0:
                        n_reconstructions += 1
                        true_used[true_id] = 1
                        used[id] = 1

            if n_matchings == 0:
                n_ghosts += 1

        # Calculate reconstruction efficiency, ghost rate and clone rate

        if n_tracks > 0:
            self.reconstruction_efficiency_ = 1. * n_reconstructions / n_tracks
            self.ghost_rate_ = 1. * n_ghosts / n_tracks
            self.clone_rate_ = 1. * (len(params) - n_reconstructions - n_ghosts) / n_tracks
        else:
            self.reconstruction_efficiency_ = 0.
            self.ghost_rate_ = 0.
            self.clone_rate_ = 0.
