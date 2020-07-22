import functools
from abc import ABC
from typing import List, cast


def eid_required(func):
    @functools.wraps(func)
    def check_id(self, *args, **kwargs):
        if self.entityId:
            return func(self, *args, **kwargs)
        else:
            raise Exception('entityId is required for this operation')

    return check_id


class Base(ABC):
    def __init__(self, client):
        """Base model class

        Args:
            client (BadgrClient): The BadgerClient instance to
            use for sending requests
        """
        self.client = client
        self.entityId = None
        self.data = None

    def set_data(self, data):
        """Populate the data

        Args:
            data (dict): The data to populate
        """
        self.data = data
        if 'entityId' in data:
            self.entityId = data['entityId']

        return self

    def get_entity_ep(self) -> str:
        return self.ENDPOINT + '/{}'.format(self.entityId)

    @eid_required
    def delete(self) -> dict:
        """Delete entity
            Returns:
                Response dict
        """
        ep = self.get_entity_ep()
        response = self.client._call_api(ep, 'DELETE')

        return response

    @eid_required
    def update(self) -> dict:
        """Update entity
        Returns:
            Response dict
        """
        ep = self.get_entity_ep()
        response = self.client._call_api(ep, 'PUT', data=self.data)
        # Fetch again to update self
        self.fetch(self.get_entity_ep())
        return response

    @eid_required
    def fetch(self):
        """Fetch entity from entityId
        """
        ep = self.get_entity_ep()
        response = self.client._call_api(ep)

        result = response['result'][0]

        self.set_data(result)

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self.entityId)


class Assertion(Base):

    ENDPOINT = '/v2/assertions'

    def create(
            self,
            badgeclass,
            recipient_email,
            narrative=None,
            evidence=None,
            expires=None,
            issued_on=None,
            notify=True,
            ) -> 'Assertion':
        """Issue an Assetion to a single recipient

        Args:
            badgeclass (string): entityId of the badgeclass to issue
            recipient_email (string): Email of the person to issue the badge
            narrative (string, optional): Describe how to badge was earned
            evidence (list[dict { url (string), narrative (string) }],
                optional): Evidence to attach to this assertion,
            expires (str, optional): The expiry date of the assertion
                ISO8601 formated datetime
            issued_on (str, optional): Override the issue date
                ISO8601 formated datetime
            notify (bool, optional): Should the recipient be notified
        """
        # TODO: add other types of recipient identifiers
        payload = {
            'recipient': {
                'type': 'email',
                'identity': recipient_email,
            },
            'narrative': narrative,
            'evidence': evidence,
            'notify': notify,
            'expires': expires,
            'issuedOn': issued_on,
        }

        response = self.client._call_api(
            BadgeClass.ENDPOINT + '/{}/assertions'.format(badgeclass),
            'POST',
            data=payload)

        self.set_data(response['result'][0])

        return self

    @eid_required
    def revoke(self, reason) -> dict:
        """Revoke this assertion
        Args:
            reason (string): Reason of revocation
        Returns:
            dict: API response dict
        """
        ep = Assertion.ENDPOINT + '/{}'.format(self.entityId)
        response = self.client._call_api(ep, 'DELETE')

        return response


class BadgeClass(Base):

    ENDPOINT = '/v2/badgeclasses'

    def create(
        self,
        name,
        image,
        description,
        issuer_eid,
        criteria_text=None,
        criteria_url=None,
        alignment=None,
        tags=None,
        expires=None
    ) -> 'BadgeClass':
        """Create a new badgeclass

        Args:
            name (string): Name of the badge
            image (string): base64 encoded png/svg image
            description (String): Short description of the badge
            issuer_eid (bool): entityId of issuer to use to issue the badge
            criteria_text (string, optional): The criteria of earning the badge
            criteria_url (string, optional): Link of the criteria to earn the
            badge.
                Defaults to None.
            alignment (list[dict {
                    "targetName": "string",
                    "targetUrl": "string",
                    "targetDescription": "string",
                    "targetFramework": "string",
                    "targetCode": "string"
                    }] , optional): Alignments. Defaults to None.
            tags (list [string], optional): List of tags. Defaults to None.
            expires (dict {
                "amount":	"string"
                "duration":	"string"
                }, optional): Expiry of the badge. Defaults to None.
        Raises:
            Exception: At least one of criteria_text and \
                criteria_url is required's
        """
        if not (criteria_text or criteria_url):
            raise Exception('At least one of criteria_text and \
                criteria_url is required')

        payload = {
            'name': name,
            'image': image,
            'issuer': issuer_eid,
            'description': description,
            'criteria_text': criteria_text,
            'criteria_url': criteria_url,
            'alignments': alignment if alignment else [],
            'tags': tags if tags else [],
            'expires': expires,
        }

        response = self.client._call_api(
            BadgeClass.ENDPOINT,
            'POST',
            data=payload)
        self.set_data(response['result'][0])

        return self

    @eid_required
    def fetch_assertions(self, recipient=None, num=None) -> List[Assertion]:
        """
        Get a list of Assertions for this badgeclass

        Args:
            recipient (string, optional): Filter by recipient
            num (string, optional): Request pagination
                of results
        """
        ep = BadgeClass.ENDPOINT + '/{}/assertions'.format(self.entityId)
        response = self.client._call_api(ep)
        result = cast(
            List[Assertion],
            self.client._deserialize(response['result']))
        return result

    @eid_required
    def issue(
            self,
            recipient_email,
            narrative=None,
            evidence=None,
            expires=None,
            issued_on=None,
            notify=True) -> 'Assertion':
        """Create a new assertion of this badge

        Args:
            recipient_email (string): Email of the person to issue the badge
            narrative (string, optional): Describe how to badge was earned
            evidence (list[dict { url (string), narrative (string) }],
                optional): Evidence to attach to this assertion,
            expires (str, optional): The expiry date of the assertion
                ISO8601 formated datetime
            issued_on (str, optional): Override the issue date
                ISO8601 formated datetime
            notify (bool, optional): Should the recipient be notified
        """
        new_assertion = Assertion(self.client).create(
            self.entityId,
            recipient_email,
            narrative,
            evidence,
            expires,
            issued_on,
            notify
        )

        return new_assertion


class Issuer(Base):

    V1_ENDPOINT = '/v1/issuer/issuers/{slug}/staff'
    ENDPOINT = '/v2/issuers'

    def create(self, name, description, email, url, image=None) -> 'Issuer':
        """Create a new Issuer

        Args:
            name (string): Name of issuer
            description (string): Description of issuer
            email (string): Verified email of the owner, email must be one
            of your verified addresses.
            url (string): Website URL
            image (string): bade64 encoded string (data-uri)
        """
        payload = {
            'name': name,
            'description': description,
            'email': email,
            'url': url,
            'image': image
        }

        response = self.client._call_api(Issuer.ENDPOINT, 'POST', data=payload)
        self.set_data(response['result'][0])

        return self

    @eid_required
    def fetch_assertions(self) -> List[Assertion]:
        """Get list of assertions for this issuer
        """
        ep = Issuer.ENDPOINT + '/{}/assertions'.format(self.entityId)
        response = self.client._call_api(ep)
        result = cast(
            List[Assertion],
            self.client._deserialize(response['result']))

        return result

    @eid_required
    def fetch_badgeclasses(self) -> List[BadgeClass]:
        """Get a list of BadgeClasses for this issuer
        """
        ep = Issuer.ENDPOINT + '/{}/badgeclasses'.format(self.entityId)
        response = self.client._call_api(ep)
        result = cast(
            List[BadgeClass],
            self.client._deserialize(response['result'])
        )

        return result

    @eid_required
    def create_badgeclass(
        self,
        name,
        image,
        description,
        criteria_text=None,
        criteria_url=None,
        alignment=None,
        tags=None,
        expires=None
    ) -> BadgeClass:
        """Create a badgeclass for this issuer

        Args:
            name (string): Name of the badge
            image (string): base64 encoded png/svg image (data-uri string)
            description (String): Short description of the badge
            criteria_text (string, optional): The criteria of earning the badge
            criteria_url (string, optional): Link of the criteria to earn
            the badge. Defaults to None.
            alignment (dict {
                    "targetName": "string",
                    "targetUrl": "string",
                    "targetDescription": "string",
                    "targetFramework": "string",
                    "targetCode": "string"
                    } , optional): Alignments. Defaults to None.
            tags (list [string], optional): List of tags. Defaults to None.
            expires (dict {
                "amount":	"string"
                "duration":	"string"
                }, optional): Expiry of the badge. Defaults to None.
        Raises:
            Exception: At least one of criteria_text and \
                criteria_url is required's
        """
        badge_class = BadgeClass(self.client).create(
            name,
            image,
            description,
            self.entityId,
            criteria_text,
            criteria_url,
            alignment,
            tags,
            expires,
        )

        return badge_class

    @eid_required
    def edit_staff(self, action: str, email: str, role: str) -> dict:
        """Edit the staff list of this issuer

        Args:
            action (str): One of 'add', 'modify' or 'remove'
            email (str): Email of the staff
            role (str): One of 'owner', 'editor', or 'staff'
        """

        if action not in ['add', 'modify', 'remove']:
            raise Exception(
                "Action must be one of 'add', 'modify' or 'remove'")

        if role not in ['owner', 'editor', 'staff']:
            raise Exception(
                "Action must be one of 'owner', 'editor', or 'staff'"
            )

        payload = {
            'action': action,
            'email': email,
            'role': role
        }

        response = self.client._call_api(
            Issuer.V1_ENDPOINT.format(slug=self.entityId),
            'POST',
            data=payload
            )

        self.fetch(self.get_entity_ep())

        return response
