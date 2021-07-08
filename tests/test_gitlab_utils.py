from pullapprove.models.gitlab.utils import shorten_report_url


def test_shorten_report_url():
    original = "http://pullapprove-public-staging.s3-website-us-west-2.amazonaws.com/report/?url=https%3A//pullapprove-storage-staging.s3.amazonaws.com/reports/a101845e-e0c7-4caa-ae43-7ad15711219f.json%3FAWSAccessKeyId%3DAKIAQEX3NIPJJUG7M5KF%26Signature%3DDl39v1IzRaW1IKpHj7hNI84aOrc%253D%26Expires%3D1584052009&fingerprint=123456789"
    shortened = shorten_report_url(original)
    assert (
        shortened
        == "http://pullapprove-public-staging.s3-website-us-west-2.amazonaws.com/report/?t=a101845e-e0c7-4caa-ae43-7ad15711219f.json%3FAWSAccessKeyId%3DAKIAQEX3NIPJJUG7M5KF%26Signature%3DDl39v1IzRaW1IKpHj7hNI84aOrc%253D%26Expires%3D1584052009&f=123456789"
    )
    assert len(shortened) < 255
