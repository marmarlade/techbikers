from rest_framework import generics, serializers
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from server.core.models.rides import Ride, RideRiders
from server.core.models.sales import Sale
from server.api.serializers.rides import RideSerializer, RideRiderSerializer
from server.api.serializers.riders import RiderSerializer
from server.api.permissions import IsOwner, RiderIsAccepted


class RidesList(generics.ListCreateAPIView):
    model = Ride
    queryset = Ride.objects.all()
    serializer_class = RideSerializer


class RideDetails(generics.RetrieveUpdateAPIView):
    model = Ride
    queryset = Ride.objects.all()
    serializer_class = RideSerializer
    lookup_field = 'id'


class RideRidersList(generics.ListCreateAPIView):
    def get_queryset(self):
        return User.objects.filter(
            ride__id=self.kwargs.get('id'),
            rideriders__status=RideRiders.REGISTERED)

    def get_serializer_class(self):
        """
        We want to return a list of the riders that are on the ride when the action
        is 'list'. When the action is 'create' we want to try and create a new
        RideRider object for the current user on the current ride so use the
        RideRiderSerializer instead.
        """
        if self.request.method == 'POST':
            return RideRiderSerializer
        return RiderSerializer

    def perform_create(self, serializer):
        ride = Ride.objects.get(id=self.kwargs.get('id'))
        user = self.request.user

        serializer.save(
            user=user,
            ride=ride,
            paid=False,
            status=RideRiders.PENDING)


class RideRiderDetails(generics.RetrieveAPIView):
    model = RideRiders
    queryset = RideRiders.objects.all()
    serializer_class = RideRiderSerializer
    permission_classes = (IsOwner,)

    def get_object(self):
        queryset = self.get_queryset()
        filter = {
            'ride__id': self.kwargs.get('id'),
            'user__id': self.kwargs.get('rider_id')
        }
        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj


class RideRiderCharge(generics.UpdateAPIView):
    model = RideRiders
    serializer_class = RideRiderSerializer
    permission_classes = (IsOwner, RiderIsAccepted)
    lookup_field = 'user__id'
    lookup_url_kwarg = 'rider_id'

    def get_queryset(self):
        return RideRiders.objects.filter(ride__id=self.kwargs.get('id'))

    def perform_update(self, serializer):
        """
        Charge the user for the ride fee and then update the status of
        their RideRider entry. The current status must be 'accepted'
        and the logged in user must be the owner of the record.
        """
        request = self.request
        ride = Ride.objects.get(id=self.kwargs.get('id'))
        if ride.price > 0:
            sale = Sale.charge(
                request.data.get('token'),
                ride.chapter.private_key,
                int(ride.price * 100),
                ride.currency,
                "Techbikers {0}: {1}".format(ride.name, request.user.email))
            sale.rider_id = request.user.id
            sale.save()

            serializer.save(status=RideRiders.REGISTERED, paid=True, sale=sale)
        else:
            serializer.save(status=RideRiders.REGISTERED)