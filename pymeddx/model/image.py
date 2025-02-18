import base64
import json
import sqlite3

from sqlalchemy import Column, Integer, String, Table, Enum, select, func, and_
from sqlalchemy.orm import relationship
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.hybrid import hybrid_property
from pathlib import Path

from utils.database import Base, session
from model.diagnosis import Diagnosis, Diagnoses, association_table, ForeignKey
from utils.tools import load_dicom
from utils.logger import logger


# image_qtype2 = Table('image_qtype2', Base.metadata,
#                           Column("image_id", Integer, ForeignKey("image.id")),
#                           Column("question_id", Integer, ForeignKey("qtype2.id")))


class Image(Base):
    __tablename__ = "image"
    id        = Column(Integer, primary_key=True, autoincrement=True)
    root      = Column(String, nullable=False)
    filename  = Column(String(50), nullable=False, unique=True)
    dataset   = Column(String, nullable=True)
    model     = Column(String, nullable=True)
    group_id  = Column(Integer, nullable=True)
    type      = Column(String, nullable=True)

    questions    = relationship("QuestionType1", back_populates="image")
    diagnoses = relationship("Diagnosis", secondary=association_table, back_populates="images")
    copeland_score = relationship("CopelandScore", back_populates="image")

    # questions_t2 = relationship("QuestionType2", secondary=image_qtype2, back_populates="images")
    # TODO if needed add the other direction of the relationship Image - QuestionType2
    # at the moment, there is implementation for relationship QuestionType2 -> Image
    # direction Image -> QuestionType2 is computationally and not needed at the moment

    @property
    def fullpath(self):
        return Path(self.root) / self.filename

    @hybrid_property
    def name(self):
        """
        Name of the file without a file extension.
        """
        return self.filename[:self.filename.rfind('.')]

    def __init__(self, filepath, model=None, dataset=None, gid=None):
        filepath = Path(filepath)
        self.filename = filepath.name
        self.dataset = dataset
        self.model = model
        self.root = str(filepath.parent)
        self.image_group_id = gid

    def __repr__(self):
        return "<Image (\n\tid: '{}',\n\troot: '{}',\n\tdataset: '{}',\n\tmodel: '{}',\n\tfilename: '{}',\n\tquestions: '{}'\n)>".format(
            str(self.id),
            self.root,
            self.dataset,
            self.model,
            self.filename,
            str(len(self.questions))
        )

    def encode_to_base64(self):
        """
        Encode an image file associated to Image object as a Base64 string.
        The image file is the file located at the path self.root + self.filename.

        :return: The base64-encoded string representation of the image.
        """
        image_path = Path(self.root) / self.filename;
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
        encoded_string = base64.b64encode(image_data).decode("utf-8")
        return encoded_string

    def exists(self):
        return (Path(self.root) / self.filename).exists()


class Images:

    @staticmethod
    def insert(image):
        try:
            session.add(image)
        except:
            session.rollback()
            raise
        else:
            session.commit()

    @staticmethod
    def bulk_insert(images):
        try:
            for image in images:
                try:
                    for d in image.diagnoses:
                        session.add(d)
                    session.add(image)
                    session.commit()
                except sqlite3.IntegrityError:
                    logger.error(f"Image {image.filename} will not be saved to the database, since the image with the "
                                 f"same filename already exists.")
                    session.rollback()
        except:
            session.rollback()
        finally:
            session.commit()

    @staticmethod
    def update(image):
        try:
            session.merge(image)
        except:
            session.rollback()
            raise
        else:
            session.commit()

    @staticmethod
    def delete(image):
        raise NotImplementedError

    @staticmethod
    def get_all():
        return session.query(Image).all()

    @staticmethod
    def get_max_image_group():
        """
        Get maximum group ID based on images already in a database. If none of the images
        have an associated ID, zero is returned.

        :return: Maximal image group ID associated with images inserted into the database.
        """
        with session.no_autoflush:
            max_group_id = session.query(func.max(Image.group_id)).scalar()
        if max_group_id is None:
            max_group_id = 0
        return max_group_id

    @staticmethod
    def get_min_image_group():
        """
        Get minimum group ID based on images already in a database. If none of the images have an
        associated ID, None is returned.

        :return: Minimal image group ID associated with images inserted into the database.
        """
        return session.query(func.min(Image.group_id)).scalar()

    @staticmethod
    def load_images(qtype, directory, extensions, metadata_file=None):
        """
        Loads images with specific file extensions from a given directory. For each image
        an object of Image class is created and added to the `images` collection. If the
        collection is not empty, newly created Image objects are appended to the collection.

        :param qtype: TODO
        :param directory: Path of str object pointing to the directory containing images.
        :param extensions: A list of valid image extensions with dot, e.g. [".png", ".jpg"].
            Extension list is case insensitive.
        :param metadata_file: TODO
        :return:
        """
        logger.info(f"Loading images for questionnaire type {qtype}.")
        qtype = int(qtype)

        if type(directory) is not Path:
            directory = Path(directory)

        if not directory.exists():
            logger.error(f"Cannot load images because directory {directory} does not exist.")
            raise NotADirectoryError(f"Cannot load images because directory {directory} does not exist.")

        # all extensions to lowercase
        extensions = [ext.lower() for ext in extensions]
        extensions = extensions[0]
        logger.info(f"Image extensions to be loaded {extensions}.")
        logger.info(f"Loading images from {directory}...")

        # extract png from dicom images
        dicom_paths = Path(directory).glob("*")
        if ".dicom" in extensions or ".dcm" in extensions:
            for path in dicom_paths:
                if path.suffix in ['.dcm', '.dicom']:
                    _ = load_dicom(path)

        # load regular images
        images = list()
        img_paths = Path(directory).glob("*")

        # image loading for questionnaire type 1
        if qtype == 1:
            images = list()
            for img_path in img_paths:
                # check if file extension is supported
                if img_path.suffix.lower() in extensions:
                    # if the file is in dicom format, change the pathname to the extracted png image
                    if img_path.suffix.lower() in ['.dcm', '.dicom']:
                        img_path = img_path.with_suffix('.png')
                    img = Image(img_path, dataset=img_path.parent.name)

                    if img.exists():
                        images.append(img)
                    else:
                        logger.warning(f"[WARNING] The image on path '{img.fullpath}' does not exist, so it cannot "
                                       f"be stored in a database.")
        # image loading for questionnaire type 2
        elif qtype == 2:
            images = list()
            for img_path in img_paths:
                if img_path.suffix.lower() in extensions:
                    img_parts = img_path.stem.split('-')
                    if len(img_parts) != 1:
                        dataset = img_parts[2]
                        model = img_parts[1]
                    else:
                        dataset = "reference"
                        model = ""
                    img = Image(
                        filepath=img_path,
                        dataset=dataset,
                        model=model
                    )
                    images.append(img)
        else:
            logger.error(f"Unsupported question type '{qtype}'.")

        logger.info(f"Loaded {len(images)} images.")

        if len(images) != 0:
            if metadata_file is None:
                default_metadata = str(Path(directory).resolve().name).lower()
                metadata_file = Path(directory).resolve() / (default_metadata + ".json")
                logger.info(f"Metadata filename is not specified, it is assumed that there is metadata file in "
                            f"directory {directory}, named  {metadata_file}")
            else:
                metadata_file = Path(directory) / metadata_file
            logger.info(f"Trying to load image metadata from a file {metadata_file}.")
            if not (metadata_file.exists() and metadata_file.is_file()):
                logger.warning(f"Metadata file {metadata_file} not found or is not a file! Skipping image metadata "
                               f"loading.")
            else:
                Images._load_image_metadata(images=images, metadata_filepath=metadata_file)
                logger.info(f"Successfully loaded image metadata.")

        Images.bulk_insert(images)      # add new images to database
        logger.info(f"Inserted {len(images)} images into the database.")

    @staticmethod
    def _load_image_metadata(images, metadata_filepath):
        """
        Load image metadata from a metadata file.

        File stores metadata per image per line. Each line starts with full or partial image name that is followed with
        metadata separated by commas.

        E.g.
            000000,diabetic_retinopathy,vein_occlusion
        where 000000 is part of the image filename, and `diabetic_retinopathy` and `vein_occlusion` are two metadata
        strings for the image.

        :param images: Images for which to load metadata.
        :param metadata_filepath: Relative or absolute path to the metadata file.
        :return: None
        """

        with open(metadata_filepath, "r") as metf:
            metadata = json.load(metf)

        for image_metadata in metadata:
            for image in images:
                image_diagnoses = list()
                if image_metadata["image_name"] in image.name:
                    # process diagnosis data
                    try:
                        diagnoses = image_metadata["diagnoses"]
                        if diagnoses is not None and len(diagnoses) != 0:
                            for diagnosis in diagnoses:
                                d = Diagnoses.insert(name=diagnosis["name"], token=diagnosis["token"])
                                image_diagnoses.append(d)
                            image.diagnoses = image_diagnoses
                    except KeyError:
                        image.diagnoses = None

                    # process image group data if it exist
                    try:
                        group_id = int(image_metadata["group"])
                        if group_id is not None:   # image doesn't necessarily belong to any group
                            image.group_id = group_id + Images.get_max_image_group()
                    except KeyError:
                        image.group_id = None

                    # get image type if exists for the image
                    try:
                        type = image_metadata["type"]
                        if type is not None:        # image type can be unknown
                            image.type = type
                    except KeyError:
                        image.type = None

    @staticmethod
    def get_whole_group(gid):
        """

        :param gid:
        :return:
        """
        images = session.query(Image).where(Image.group_id == gid).all()
        if len(images) == 0:
            return None
        return images

    @staticmethod
    def get_by_name(image_filenames):
        """

        :param image_filenames:
        :return:
        """
        logger.info(f"Load from database images with names {image_filenames}.")
        filters = []
        for filename in image_filenames:
            filters.append(Image.filename == filename)
        return session.query(Image).filter(*filters).all()

    @staticmethod
    def get_by_id(iid):
        """
        Get image from database by id.
        """
        # logger.info(f"Load from database images with names {image_filenames}.")
        r = session.query(Image).where(Image.id == iid).one()
        if r is None:
            logger.warning(f"Image with ID {iid} could not be found in a database.")
        return r

    @staticmethod
    def get_original_for_segmap(segmap):
        """
        Searches for the original color image in a database for a corresponding segmentation mask. It is assumed that
        the segmentaion mask is named similar to the pattern: <number>-<network>-<dataset>.<extension> and that the
        original is named like <number>.<extension>

        :param segmap: An instance of Image class representing a segmentation map with filename similar to
            <number>-<network>-<dataset>.
        :return:
        """
        assert segmap is not None
        filename = segmap.filename.split('-')[0]    # for segmentation mask filename like <number>-<network>-<dataset>
                                                    # extracts <number> and uses it to query for the original image of
                                                    # that name

        try:
            return session.query(Image).where(and_(Image.type == "original", Image.filename.contains(filename))).one()
        except NoResultFound:
            print(f"I cannot find an original for a segmentation map {segmap.filename}.")
