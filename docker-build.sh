BASE_IMAGE_TAG=py-3131-v1 # py-3.11.11-v1, update this to rebuild the base image

UV_VERSION=latest

DOCKER_REGISTRY_HOST=registry.314ecorp.tech
BASE_IMAGE=$DOCKER_REGISTRY_HOST/launchpad-app-base
IMAGE=$DOCKER_REGISTRY_HOST/launchpad-app

if [ -z "$1" ]; then
    echo "Image tag is required"
    exit 1
fi

IMAGE_TAG=$1
IMAGE_TAG=${IMAGE_TAG//\//-}  # replace / with -, eg: impr/docker -> impr-docker

if [ "$2" == "--push" ]; then
    PUSH=true
else
    PUSH=false
fi

# check if the base image exists
docker manifest inspect -v $BASE_IMAGE:$BASE_IMAGE_TAG
if [ $? -ne 0 ]; then
    echo "Base image $BASE_IMAGE:$BASE_IMAGE_TAG does not exist, building ..."
    docker build \
        -t $BASE_IMAGE:$BASE_IMAGE_TAG \
        -f Dockerfile.base . \
        --platform linux/amd64
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Failed to build base image"
        exit $exit_code
    fi
    echo "Base image built $BASE_IMAGE:$BASE_IMAGE_TAG"
fi

echo "Building image $IMAGE:$IMAGE_TAG ..."
docker build \
    -t $IMAGE:$IMAGE_TAG \
    -f Dockerfile .  \
    --platform linux/amd64 \
    --build-arg UV_VERSION=$UV_VERSION \
    --build-arg BASE_IMAGE_TAG=$BASE_IMAGE_TAG \

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Failed to build image"
    exit $exit_code
fi

echo "Image built $IMAGE:$IMAGE_TAG"
# print size of the images
docker image ls

if [ "$PUSH" = true ]; then
    echo "Pushing images to $DOCKER_REGISTRY_HOST"
    docker push $BASE_IMAGE:$BASE_IMAGE_TAG
    echo "Pushed $BASE_IMAGE:$BASE_IMAGE_TAG"
    docker push $IMAGE:$IMAGE_TAG
    echo "Pushed $IMAGE:$IMAGE_TAG"
fi