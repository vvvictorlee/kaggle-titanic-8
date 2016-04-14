#!/usr/bin/python

import pandas as pd
import numpy as np
import sklearn.preprocessing as preprocessing
from sklearn.linear_model import LogisticRegression
from sklearn import cross_validation
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC


def fill_missing_ages(data):
    """Fill missing age using RandomForestRegressor
    The Regressor is trained with the data which has ages,
    The features for training are Age, SibSP, Parch, Fare, and Pclass
    Return the data filled with ages, and also the trained Regressor
    """

    # Selete features for training
    age_data = data[['Age', 'SibSp', 'Parch', 'Fare', 'Pclass']]

    # Divide passengers into with and without age
    with_age = age_data.loc[age_data['Age'].notnull()]
    without_age = age_data.loc[age_data['Age'].isnull()]
    # In the case that predict does not work  when withou_age is null
    if without_age.shape[0] == 0:
        without_age = pd.DataFrame({'Age': None, 'SibSp': {'1': 0},
                                    'Parch': {'1': 0}, 'Fare': {'1': 0},
                                    'Pclass': {'1': 0}})
    # X is the features
    X = with_age.iloc[:, 1:]
    Y = with_age.iloc[:, 0]

    # Train RandomForestRegressor
    alg = RandomForestRegressor(n_estimators=1000, n_jobs=-1, random_state=0)
    alg.fit(X, Y)

    # Predict age fill age
    data.loc[data['Age'].isnull(), 'Age'] = alg.predict(without_age.iloc[:, 1:])

    return data, alg


def set_cabin_type(data):
    """Set cabin into 2 types: with or without value
    Return the data whose Cabin column is replace by Yes
    """

    data.loc[data['Cabin'].notnull(), 'Cabin'] = 'Yes'
    data.loc[data['Cabin'].isnull(), 'Cabin'] = 'No'

    return data


def scale_data(data, param):
    """Scale the colomns of  param
    Return scaled colomn of data
    """
    scaler = preprocessing.StandardScaler()
    scale_param = scaler.fit(data[param])
    scaled = pd.DataFrame({param: scaler.transform(data[param], scale_param)})

    return scaled


def extract_features(data):
    """Features extraction and selection method,
    Return features extracted, the features are DataFrame objective
    """

    # Set cabin type
    data = set_cabin_type(data)
    # Fill Embarked missing data with S
    data["Embarked"] = data["Embarked"].fillna("S")
    # Fill Fare missing data with the median
    data['Fare'] = data['Fare'].fillna(data['Fare'].median())

    # Fill missing value of ages
    # Fill null data with age generated by Random Forest
    if data.loc[data['Age'].isnull()].shape[0] != 0:
        data, alg = fill_missing_ages(data)
    # Or we can fill null data with median of age
    # data['Age'] = data['Age'].fillna(data['Age'].median())

    # Extract dummies of Pclass, Sex, Cabin, Embarked
    pclass = pd.get_dummies(data['Pclass'], prefix='Pclass')
    sex = pd.get_dummies(data['Sex'], prefix='Sex')

    cabin = pd.get_dummies(data['Cabin'], prefix='Cabin')
    embarked = pd.get_dummies(data['Embarked'], prefix='Embarked')
    sibsp = data['SibSp']
    parch = data['Parch']
    data['FamilySize'] = data['SibSp'] + data['Parch']
    family_size = data['FamilySize']

    # Scale Age
    age = scale_data(data, 'Age')
    # Scale Fare
    fare = scale_data(data, 'Fare')
    # Scale Sibsp
    sibsp = scale_data(data, 'SibSp')
    # Scale Parch
    parch = scale_data(data, 'Parch')
    # Scale FamilySize
    family_size = scale_data(data, 'FamilySize')

    # Concate features
    features = pd.concat([pclass, sex, cabin, embarked, age, fare,
                          sibsp, parch, family_size], axis=1)

    return features


def train_model(data, algs):
    """Train model with all data
    Return the classifier trained and the features extracted
    """

    # Extract train features
    features = extract_features(data)

    # Train model
    for alg in algs:
        alg.fit(features, data['Survived'])

    return algs, features


def cross_validation_evaluation(data, algs):
    """Train system with cross validation of the data, with the input algorithms
    Then evaluate the trained system,
    Return the accuracy
    """

    # Extract train features
    features = extract_features(data)

    # Set random_state to ensure to get the same splits every time we run this
    kf = cross_validation.KFold(features.shape[0], n_folds=3,
                                shuffle=False, random_state=1)

    predictions = []
    for train, test in kf:
        ensemble_predictions = []
        for alg in algs:
            alg.fit(features.iloc[train, :], data['Survived'].iloc[train])
            ensemble_predictions.append(alg.predict(features.iloc[test, :]))
        test_prediction = ensemble_predictions[0]
        for i in range(1, len(algs)):
            test_prediction += ensemble_predictions[i]
        test_prediction = test_prediction / len(algs)
        test_prediction[test_prediction > 0.5] = 1
        test_prediction[test_prediction <= 0.5] = 0
        predictions.append(test_prediction)

    predictions = np.concatenate(predictions, axis=0)
    # Calculate CV accuracy
    error_nb = sum(abs(predictions - pd.Series.as_matrix(data.Survived)))
    accuracy = 1 - error_nb / data.shape[0]

    return accuracy


def submission(data, classifiers):
    """Evaluate test data"""

    # Extract test features
    features = extract_features(data)
    # Predict test data
    predictions = []
    for classifier in classifiers:
        prediction = classifier.predict(features)
        predictions.append(prediction)

    test_prediction = predictions[0]
    for i in range(1, len(classifiers)):
        test_prediction += predictions[i]
    test_prediction = test_prediction / len(classifiers)
    test_prediction[test_prediction > 0.5] = 1
    test_prediction[test_prediction <= 0.5] = 0
    submission = pd.DataFrame({'PassengerId': data['PassengerId'],
                               'Survived': test_prediction})
    submission.to_csv('Titanic.csv', index=False)
    print('\n\nCongras, you\'v finished the prediction, you can submit it now')

    return submission

# main
if __name__ == '__main__':

    # Load train data
    train_data = pd.read_csv('data/train.csv')
    # Define ensembling classifiers
    algs = [
        LogisticRegression(),
        LinearSVC(),
        RandomForestClassifier()
    ]
    # Use CV to evaluate the accuracy
    accuracy = cross_validation_evaluation(train_data, algs)
    print("accuracy for the training data is:", accuracy)

    # Train with all the data
    # alg, features = train_model(train_data)

    # print(pd.DataFrame({'features': list(features.columns),
    #                     'coef': list(alg.coef_.T)}))

    # Predict test data, and make a submission
    # Load test data
    # test_data = pd.read_csv('data/test.csv')
    # Save the result in .csv file
    # submission = submission(test_data, alg)

    # Use ensemble classifiers
    """
    train_data = pd.read_csv('data/train.csv')
    features = extract_features(train_data)
    algs = [
        LogisticRegression(),
        LinearSVC(),
        GaussianNB()
    ]
    for alg in algs:
        alg.fit(features, train_data['Survived'])

    test_data = pd.read_csv('data/test.csv')
    features = extract_features(test_data)
    predictions = []
    for alg in algs:
        predictions.append(alg.predict(features))
    predictions = (predictions[0] + predictions[1]) / len(algs)
    predictions[predictions > 0.5] = 1
    predictions[predictions <= 0.5] = 0
    submission = pd.DataFrame({'PassengerId': test_data['PassengerId'],
                               'Survived': predictions})
    submission.to_csv('Titanic.csv', index=False)
    print('\n\nCongras, you\'v finished the prediction, you can submit it now')
    """
